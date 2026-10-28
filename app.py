"""Local classroom banking demonstration. Start with: python app.py"""
import os
import re
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

import pymysql
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from db import close_db, query, transaction

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  MAX_CONTENT_LENGTH=128 * 1024)
app.teardown_appcontext(close_db)


@app.template_filter("money")
def money(value):
    return f"{Decimal(value or 0):,.2f}"


@app.context_processor
def form_helpers():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return {"csrf_token": session["csrf"], "today": date.today().isoformat()}


@app.before_request
def protect_forms():
    if request.method == "POST":
        expected = session.get("csrf", "")
        supplied = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, supplied):
            abort(400, description="Form expired. Open the page again and retry.")


def field(name, maximum=255, required=True):
    value = request.form.get(name, "").strip()
    if required and not value:
        raise ValueError(f"Please enter {name.replace('_', ' ')}.")
    if len(value) > maximum:
        raise ValueError(f"{name.replace('_', ' ')} is too long (maximum {maximum}).")
    return value or None


def positive_id(value):
    try:
        number = int(value)
        if number <= 0:
            raise ValueError
        return number
    except (TypeError, ValueError):
        raise ValueError("Select a valid customer, branch, or account.") from None


def parse_amount(value):
    try:
        amount = Decimal(value)
        if (not amount.is_finite() or amount <= 0 or amount > Decimal("1000000000")
                or amount != amount.quantize(Decimal("0.01"))):
            raise ValueError
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Enter a positive amount, up to 1,000,000,000, with at most two decimal places.") from None


def transfer_reference(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid operation reference. Reopen the money page.") from None


def log_entry(cursor, account_id, kind, amount, description, reference):
    cursor.execute("""INSERT INTO bank_transaction
        (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
        VALUES (%s, %s, %s, %s, %s, 'SUCCESS')""",
        (account_id, kind, amount, description, reference))


def perform_cash(account_id, kind, amount, reference, description):
    """Lock account, validate, update balance and insert ledger entry atomically."""
    if kind not in ("DEPOSIT", "WITHDRAWAL"):
        raise ValueError("Invalid operation.")
    amount = parse_amount(str(amount))
    with transaction() as cursor:
        cursor.execute("SELECT * FROM account WHERE AccountID=%s FOR UPDATE", (account_id,))
        account = cursor.fetchone()
        if not account or account["Status"] != "Active":
            raise ValueError("Choose an existing active account.")
        if kind == "WITHDRAWAL" and account["Balance"] < amount:
            raise ValueError("Insufficient balance. No money was withdrawn.")
        change = amount if kind == "DEPOSIT" else -amount
        cursor.execute("UPDATE account SET Balance=Balance+%s WHERE AccountID=%s", (change, account_id))
        log_entry(cursor, account_id, kind, amount, description, reference)


def perform_transfer(sender_id, receiver_id, amount, reference, description):
    if sender_id == receiver_id:
        raise ValueError("Sender and receiver must be different accounts.")
    amount = parse_amount(str(amount))
    with transaction() as cursor:
        # Every transfer locks accounts in the same ID order to reduce deadlocks.
        accounts = {}
        for account_id in sorted((sender_id, receiver_id)):
            cursor.execute("SELECT * FROM account WHERE AccountID=%s FOR UPDATE", (account_id,))
            account = cursor.fetchone()
            if not account or account["Status"] != "Active":
                raise ValueError("Both accounts must exist and be active.")
            accounts[account_id] = account
        if accounts[sender_id]["Balance"] < amount:
            raise ValueError("Insufficient balance. No money was transferred.")
        cursor.execute("UPDATE account SET Balance=Balance-%s WHERE AccountID=%s", (amount, sender_id))
        cursor.execute("UPDATE account SET Balance=Balance+%s WHERE AccountID=%s", (amount, receiver_id))
        log_entry(cursor, sender_id, "TRANSFER_OUT", amount, description, reference)
        log_entry(cursor, receiver_id, "TRANSFER_IN", amount, description, reference)


@app.get("/")
def index():
    stats = query("""SELECT (SELECT COUNT(*) FROM customer) AS customers,
        (SELECT COUNT(*) FROM account) AS accounts,
        (SELECT COALESCE(SUM(Balance),0) FROM account) AS balance,
        (SELECT COUNT(*) FROM bank_transaction) AS transactions""", one=True)
    recent = query("""SELECT t.*, a.AccountNumber FROM bank_transaction t
        JOIN account a ON a.AccountID=t.AccountID
        ORDER BY t.TransactionDate DESC, t.TransactionID DESC LIMIT 8""")
    return render_template("index.html", stats=stats, rows=recent)


@app.route("/customers", methods=["GET", "POST"])
def customers():
    if request.method == "POST":
        first, last = field("first_name", 60), field("last_name", 60)
        mobile, email = field("mobile", 20), field("email", 120)
        if not re.fullmatch(r"[+0-9 ()-]{7,20}", mobile):
            raise ValueError("Enter a valid phone number (7 to 20 characters).")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Enter a valid email address.")
        try:
            dob = date.fromisoformat(field("date_of_birth", 10))
        except ValueError:
            raise ValueError("Enter a valid date of birth.") from None
        if dob > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        gender = field("gender", 30)
        if gender not in ("Male", "Female", "Other", "Prefer not to say"):
            raise ValueError("Select a listed gender option.")
        address, city = field("address", 255), field("city", 80)
        with transaction() as cursor:
            cursor.execute("""INSERT INTO customer
                (FirstName, LastName, DateOfBirth, Gender, Mobile, Email, Address, City)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (first, last, dob, gender, mobile, email, address, city))
        flash("Customer registered. You can now open an account.", "success")
        return redirect(url_for("accounts"))
    rows = query("SELECT * FROM customer ORDER BY CustomerID DESC")
    return render_template("customers.html", rows=rows)


@app.route("/accounts", methods=["GET", "POST"])
def accounts():
    if request.method == "POST":
        holder_ids = sorted({positive_id(v) for v in request.form.getlist("customer_ids")})
        if not holder_ids:
            raise ValueError("Select at least one account holder.")
        branch_id = positive_id(field("branch_id"))
        kind = field("account_type", 20)
        if kind not in ("Saving", "Current", "Salary"):
            raise ValueError("Select a listed account type.")
        # A unique constraint is the final guard against a rare number collision.
        number = "KSH" + uuid4().hex[:16].upper()
        with transaction() as cursor:
            cursor.execute("""INSERT INTO account (AccountNumber, AccountType, BranchID)
                VALUES (%s,%s,%s)""", (number, kind, branch_id))
            account_id = cursor.lastrowid
            for i, customer_id in enumerate(holder_ids):
                cursor.execute("""INSERT INTO account_holder (CustomerID, AccountID, HolderType)
                    VALUES (%s,%s,%s)""", (customer_id, account_id, "Primary" if i == 0 else "Joint"))
        flash(f"Account {number} opened with a zero balance. Use Money desk to deposit.", "success")
        return redirect(url_for("accounts"))
    rows = query("""SELECT a.*, b.BranchName,
        GROUP_CONCAT(CONCAT(c.FirstName,' ',c.LastName) ORDER BY c.CustomerID SEPARATOR ', ') AS holders
        FROM account a JOIN branch b ON a.BranchID=b.BranchID
        JOIN account_holder h ON h.AccountID=a.AccountID
        JOIN customer c ON c.CustomerID=h.CustomerID
        GROUP BY a.AccountID, b.BranchName ORDER BY a.AccountID DESC""")
    return render_template("accounts.html", rows=rows,
        customers=query("SELECT CustomerID,FirstName,LastName FROM customer ORDER BY FirstName"),
        branches=query("SELECT BranchID,BranchName FROM branch ORDER BY BranchName"))


@app.route("/money", methods=["GET", "POST"])
def money_desk():
    if request.method == "POST":
        operation = field("operation", 20)
        amount = parse_amount(field("amount", 40))
        reference = transfer_reference(field("reference", 40))
        account_id = positive_id(field("account_id"))
        description = field("description", 255, required=False) or operation.replace("_", " ").title()
        if operation == "TRANSFER":
            receiver_id = positive_id(field("receiver_id"))
            perform_transfer(account_id, receiver_id, amount, reference, description)
        else:
            perform_cash(account_id, operation, amount, reference, description)
        flash(f"{operation.replace('_', ' ').title()} of INR {amount:,.2f} completed. Reference: {reference}", "success")
        return redirect(url_for("history", account_id=account_id))
    rows = query("SELECT AccountID,AccountNumber,Balance FROM account WHERE Status='Active' ORDER BY AccountID")
    return render_template("money.html", accounts=rows, reference=str(uuid4()))


@app.get("/history")
def history():
    selected = request.args.get("account_id", "")
    selected_id = positive_id(selected) if selected else None
    sql = "SELECT t.*,a.AccountNumber FROM bank_transaction t JOIN account a ON t.AccountID=a.AccountID"
    params = ()
    if selected_id:
        sql += " WHERE t.AccountID=%s"
        params = (selected_id,)
    sql += " ORDER BY t.TransactionDate DESC,t.TransactionID DESC LIMIT 200"
    rows = query(sql, params)
    return render_template("history.html", rows=rows, selected_id=selected_id,
        accounts=query("SELECT AccountID,AccountNumber FROM account ORDER BY AccountID"))


@app.get("/directory")
def directory():
    return render_template("directory.html", branches=query("SELECT * FROM branch"),
        employees=query("""SELECT e.*,b.BranchName FROM employee e
            JOIN branch b ON b.BranchID=e.BranchID ORDER BY e.EmployeeID"""))


@app.get("/reports")
def reports():
    # Aggregate account balances before joining holders to avoid double-counting joint accounts.
    branches = query("""SELECT b.BranchName,COUNT(a.AccountID) AS accounts,
        COALESCE(SUM(a.Balance),0) AS total FROM branch b
        LEFT JOIN account a ON a.BranchID=b.BranchID GROUP BY b.BranchID,b.BranchName""")
    totals = query("""SELECT TransactionType,COUNT(*) AS entries,SUM(Amount) AS total
        FROM bank_transaction WHERE DATE(TransactionDate)=CURRENT_DATE()
        GROUP BY TransactionType""")
    return render_template("reports.html", branches=branches, totals=totals)


@app.errorhandler(ValueError)
def invalid_input(error):
    return render_template("error.html", title="Check your input", message=str(error)), 400


@app.errorhandler(pymysql.err.IntegrityError)
def integrity_error(error):
    message = ("A unique value already exists, or this payment form was already submitted. "
               "Check history before retrying. Use a fresh form for a new payment.")
    if error.args[0] == 1452:
        message = "A selected customer or branch does not exist. Refresh the page and select again."
    return render_template("error.html", title="Database rule protected your data", message=message), 400


@app.errorhandler(pymysql.MySQLError)
def database_error(error):
    # Log code only: do not expose credentials or submitted data in the browser.
    app.logger.error("MySQL operation failed, code=%s", error.args[0] if error.args else "unknown")
    return render_template("error.html", title="Database needs attention",
        message="Check that MySQL is running, .env is correct, and schema.sql and seed.sql were executed. "
                "If an operation was interrupted, check history before retrying."), 503


@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", title="Please reopen the form", message=error.description), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
