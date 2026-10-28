# Project Kashi — Banking Management System

A local classroom project using raw HTML/CSS, Flask, and MySQL. The interface is a staff demonstration workspace: it has no customer login or authorization system. Use fictional people and fictional money, on localhost only. Loans are omitted as permitted by the assignment.

## Start here — Windows

You have already created `project_kashi` in MySQL Workbench. The scripts also use `IF NOT EXISTS`, so that is fine.

1. Extract the ZIP. Open the inner **Project-Kashi** folder in VS Code or Cursor. You should see `app.py` directly inside the folder you open.
2. In MySQL Workbench, choose **File > Open SQL Script** and open `sql/schema.sql`. Execute the **entire** script using the lightning button (no text selected). Then do the same for `sql/seed.sql`, followed by `sql/database_objects.sql`. Refresh SCHEMAS. Do not paste SQL into the Python terminal.
3. In the editor terminal, run:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   These commands use the virtual environment directly. You do not need to activate it or change PowerShell execution policy.

4. Copy `.env.example` to `.env`. In PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   Open `.env` in the editor. Replace `replace_with_your_mysql_password` with the password you use in Workbench. Keep double quotes around the password, especially if it contains `#` or spaces. Confirm `DB_USER`, host, and port match your local connection. Do not share this file or upload it to GitHub.

5. Run:

   ```powershell
   .\.venv\Scripts\python.exe app.py
   ```

6. Open **http://127.0.0.1:5000** in your browser. Leave the terminal running. Stop the application with Ctrl+C.

## Tonight's demonstration sequence

1. Register fictional customers **Alex Demo** and **Sam Demo**, with different emails such as `alex@example.com` and `sam@example.com`.
2. Open one individual Saving account for each customer. Note the generated account numbers.
3. Deposit INR 5,000 into Alex's account. Deposit INR 1,000 into Sam's.
4. Withdraw INR 500 from Alex's account.
5. Transfer INR 1,000 from Alex to Sam.
6. Check balances: **Alex = INR 3,500; Sam = INR 2,000.** Total = INR 5,500.
7. Try to withdraw INR 10,000 from Alex. It must fail and leave both balances unchanged.
8. Open a third account with both customers selected, to demonstrate the many-to-many relationship.
9. Show the activity filter, branch directory, and reports.
10. Run `sql/business_queries.sql`. Query 12 should return **zero rows** (ledger matches balances).
11. Run `CALL GetCustomerAccounts(1);`, `SELECT CustomerTotalBalance(1);`, and `SELECT * FROM balance_audit;`. Replace 1 with the actual customer ID if needed. CustomerTotalBalance includes the full balance of each held account, including joint accounts; it does not calculate ownership shares.
12. Capture your own screenshots for your final report.

Do not edit Balance manually in Workbench. That bypasses the ledger. Do not delete transaction records.

## Files to understand

- `app.py`: routes, validation, account creation, money operations, error handling.
- `db.py`: connection management, query helper, and commit/rollback context manager.
- `templates/`: raw HTML with Jinja placeholders; `base.html` supplies navigation.
- `static/style.css`: responsive styling; no frontend framework or CDN.
- `sql/schema.sql`: seven tables, including the extra audit table.
- `sql/seed.sql`: two fictional branches and employees; safe to rerun.
- `sql/database_objects.sql`: view, procedure, function, trigger.
- `sql/business_queries.sql`: 12 meaningful queries including reconciliation.
- `docs/STUDY_GUIDE.md`: relationships, concepts, workflow, viva questions, report checklist.
- `docs/er_diagram.svg`: viewable ER diagram; `docs/er_diagram.mmd`: editable Mermaid source.
- `tests/test_app.py`: unit/route tests; real MySQL integration must also be checked locally.

## Requirements and database behavior

- MySQL **8.0.16 or newer**. Date defaults use expression defaults and CHECK constraints need enforcement. The setup is intended for MySQL, not SQLite.
- A Python version supported by the installed packages. The author tested on Python 3.12. Your reported Python 3.15 has not been verified here. Try the commands above; if a dependency fails to install, use Python 3.13 side by side, then create the environment using `py -3.13 -m venv .venv` (remove or rename the failed virtual environment first).
- `PyMySQL[rsa]` is the Python driver; MySQL Server remains the database. The RSA extra supports modern MySQL authentication.
- Accounts begin at zero. Every successful money operation records positive amounts with a direction/type.
- InnoDB transactions and row locks protect the affected balances. Transfers lock account IDs in ascending order. Balances and ledger entries commit together or roll back together.
- A UUID reference plus a unique `(ReferenceNumber, TransactionType)` constraint prevents the same submitted money form from applying twice. Reopen the money page for a new operation.
- The trigger writes an audit entry only; it never updates Balance, avoiding double application of money movements.
- History displays the most recent 200 successful entries. Failed requests are shown as errors, not stored as financial ledger entries.
- Backend validation, parameterized queries, CSRF tokens, HTML escaping, and a loopback-only server are included. Authentication, roles, encryption at rest, real payments, interest, and production banking controls are outside this demo.
- Changes to database objects are executed by you in Workbench. The app needs SELECT, INSERT, and UPDATE privileges on its database; avoid using a database administrator account outside a local class setup.

## Troubleshooting

**Database needs attention:** confirm MySQL Server is running, `.env` contains the right password, and all SQL scripts ran. Check Workbench's Action Output for the first error. Restart Python after changing `.env`.

**Unknown database/table:** run `schema.sql` on the same server configured in `.env`.

**No branches:** execute `seed.sql`.

**Function error 1418/1419:** some servers restrict stored functions with binary logging. Do not falsely label this function deterministic: its result changes when balances change. On your own disposable local MySQL instance, an administrator can permit trusted routine creators with `SET GLOBAL log_bin_trust_function_creators = 1;` and rerun `database_objects.sql`. This is a server-wide setting; on a shared or college server, ask the administrator instead. Restore the original setting after creating the function if required. The website works without this routine; the function demonstration still needs to be completed for the assignment.

**Port 5000 already in use:** stop the other instance, or change `port=5000` at the bottom of `app.py` and open the matching URL.

**CSRF/form expired:** open the form again. Sessions change when the app restarts unless a SECRET_KEY was configured.

**Duplicate email or operation:** use a distinct customer email. For money operations, check activity first; use a fresh form only for an actual new operation.

**Error 1213 / lock wait timeout:** that operation was interrupted. Check activity, reopen the money page, and retry if the operation is absent.

**Run tests:** `python -m pip install pytest`, then `python -m pytest -q`. These use a transactional in-memory test double to verify application orchestration and routes, not MySQL compatibility. Complete the real database demonstration above too.

## Submission

Your assignment asks you to create and understand HTML and MySQL yourself. Use this reference to rebuild/adapt those parts and prepare to explain them. Review every SQL statement and route before viva.

Create a GitHub repository named `Project-Kashi` (spaces are not supported in repository names). Upload this folder's source, SQL, documentation, and your own screenshots. Exclude `.env`, `.venv`, caches, and real personal information. A draft documentation guide is included; add screenshots and actual query outputs before calling the report complete.

## Primary references

- Flask: https://flask.palletsprojects.com/en/stable/
- PyMySQL: https://pymysql.readthedocs.io/en/latest/
- MySQL transactions: https://dev.mysql.com/doc/refman/8.4/en/commit.html
- InnoDB locking reads: https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html
