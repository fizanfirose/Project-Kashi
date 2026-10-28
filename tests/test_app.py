"""Application tests with a transaction-capable test double, NOT a MySQL emulator."""
import copy
import sys
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as banking


class Store:
    def __init__(self):
        self.accounts = {
            1: {"AccountID": 1, "AccountNumber": "KSH1", "Status": "Active", "Balance": Decimal("5000")},
            2: {"AccountID": 2, "AccountNumber": "KSH2", "Status": "Active", "Balance": Decimal("1000")},
        }
        self.entries = []
        self.locks = []
        self.fail_on_entry = None

    @contextmanager
    def transaction(self):
        snapshot = copy.deepcopy((self.accounts, self.entries))
        store = self

        class Cursor:
            row = None

            def execute(self, sql, params):
                if "FOR UPDATE" in sql:
                    store.locks.append(params[0])
                    self.row = store.accounts.get(params[0])
                elif sql.startswith("UPDATE account SET Balance=Balance+"):
                    store.accounts[params[1]]["Balance"] += params[0]
                elif sql.startswith("UPDATE account SET Balance=Balance-"):
                    store.accounts[params[1]]["Balance"] -= params[0]
                elif "INSERT INTO bank_transaction" in sql:
                    if store.fail_on_entry == len(store.entries) + 1:
                        raise RuntimeError("Simulated ledger failure")
                    if any(e[4] == params[4] and e[1] == params[1] for e in store.entries):
                        raise banking.pymysql.err.IntegrityError(1062, "Duplicate reference")
                    store.entries.append(params)
                else:
                    raise AssertionError(f"Unexpected SQL in test: {sql}")

            def fetchone(self):
                return copy.deepcopy(self.row)

        try:
            yield Cursor()
        except Exception:
            self.accounts, self.entries = snapshot
            raise


@pytest.fixture
def store(monkeypatch):
    value = Store()
    monkeypatch.setattr(banking, "transaction", value.transaction)
    return value


@pytest.mark.parametrize("value", ["0", "-5", "NaN", "Infinity", "1.001", "abc", "1000000001"])
def test_reject_bad_amounts(value):
    with pytest.raises(ValueError):
        banking.parse_amount(value)


def test_deposit_and_withdraw(store):
    banking.perform_cash(1, "DEPOSIT", Decimal("500"), "dep", "Deposit")
    banking.perform_cash(1, "WITHDRAWAL", Decimal("200"), "out", "Withdrawal")
    assert store.accounts[1]["Balance"] == Decimal("5300")
    assert [e[1] for e in store.entries] == ["DEPOSIT", "WITHDRAWAL"]


def test_transfer_balances_and_matching_reference(store):
    banking.perform_transfer(1, 2, Decimal("1000"), "same-reference", "Transfer")
    assert store.accounts[1]["Balance"] == Decimal("4000")
    assert store.accounts[2]["Balance"] == Decimal("2000")
    assert sum(a["Balance"] for a in store.accounts.values()) == Decimal("6000")
    assert [e[1] for e in store.entries] == ["TRANSFER_OUT", "TRANSFER_IN"]
    assert all(e[4] == "same-reference" for e in store.entries)
    assert store.locks == [1, 2]


def test_reverse_transfer_keeps_lock_order(store):
    banking.perform_transfer(2, 1, Decimal("100"), "reverse", "Transfer")
    assert store.locks == [1, 2]


@pytest.mark.parametrize("kind", ["WITHDRAWAL", "TRANSFER"])
def test_insufficient_funds_leaves_everything_unchanged(store, kind):
    before = copy.deepcopy(store.accounts)
    with pytest.raises(ValueError, match="Insufficient"):
        if kind == "TRANSFER":
            banking.perform_transfer(1, 2, Decimal("9000"), "fail", "Transfer")
        else:
            banking.perform_cash(1, kind, Decimal("9000"), "fail", "Withdrawal")
    assert store.accounts == before
    assert store.entries == []


def test_second_entry_failure_rolls_back_both_balances(store):
    before = copy.deepcopy(store.accounts)
    store.fail_on_entry = 2
    with pytest.raises(RuntimeError):
        banking.perform_transfer(1, 2, Decimal("100"), "fail", "Transfer")
    assert store.accounts == before
    assert store.entries == []


def test_duplicate_submission_rolls_back_second_update(store):
    banking.perform_cash(1, "DEPOSIT", Decimal("100"), "duplicate", "Deposit")
    with pytest.raises(banking.pymysql.err.IntegrityError):
        banking.perform_cash(1, "DEPOSIT", Decimal("100"), "duplicate", "Deposit")
    assert store.accounts[1]["Balance"] == Decimal("5100")
    assert len(store.entries) == 1


@pytest.mark.parametrize("sender,receiver", [(1, 1), (1, 999)])
def test_invalid_transfer(store, sender, receiver):
    with pytest.raises(ValueError):
        banking.perform_transfer(sender, receiver, Decimal("100"), "invalid", "Transfer")
    assert store.entries == []


def test_inactive_account_rejected(store):
    store.accounts[1]["Status"] = "Inactive"
    with pytest.raises(ValueError):
        banking.perform_cash(1, "DEPOSIT", Decimal("100"), "inactive", "Deposit")
    assert store.accounts[1]["Balance"] == Decimal("5000")


@pytest.mark.parametrize("path", ["/", "/customers", "/accounts", "/money", "/history", "/directory", "/reports"])
def test_empty_pages_render(monkeypatch, path):
    def fake_query(sql, params=(), one=False):
        if one:
            return {"customers": 0, "accounts": 0, "balance": Decimal(0), "transactions": 0}
        return []
    monkeypatch.setattr(banking, "query", fake_query)
    with banking.app.test_client() as client:
        response = client.get(path)
    assert response.status_code == 200
    assert "<!doctype html>" in response.text


def test_missing_csrf_rejected():
    with banking.app.test_client() as client:
        assert client.post("/money", data={}).status_code == 400


def test_post_deposit_route(monkeypatch, store):
    monkeypatch.setattr(banking, "query", lambda *args, **kwargs: [])
    with banking.app.test_client() as client:
        client.get("/money")
        with client.session_transaction() as session:
            csrf = session["csrf"]
        response = client.post("/money", data={"csrf_token": csrf, "operation": "DEPOSIT",
            "amount": "500.50", "account_id": "1", "reference": "f7f8ac15-815a-4cf6-9d88-aaf1844a3d5a"})
    assert response.status_code == 302
    assert store.accounts[1]["Balance"] == Decimal("5500.50")


def test_populated_activity_renders_and_escapes(monkeypatch):
    row = {"AccountNumber": "<script>alert(1)</script>", "TransactionType": "DEPOSIT",
           "Amount": Decimal("200"), "TransactionDate": "2026-10-27 18:00:00",
           "ReferenceNumber": "demo"}
    monkeypatch.setattr(banking, "query", lambda sql, *args, **kwargs:
                        [row] if "FROM bank_transaction" in sql else [])
    with banking.app.test_client() as client:
        response = client.get("/history")
    assert response.status_code == 200
    assert "&lt;script&gt;" in response.text
    assert "<script>alert(1)</script>" not in response.text
