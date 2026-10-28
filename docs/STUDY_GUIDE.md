# Project Kashi — design, workflow, and viva guide

This is a documentation starter, not a finished submission report. Add your name/team, your own screenshots, actual query outputs, and observed test results.

## Objective and scope

Demonstrate a database-driven local banking workspace using HTML/CSS, Flask/Python, and MySQL. Implement customer registration, individual/joint account creation, deposits, withdrawals, internal transfers, history, branches/employees, and reports. Loans and loan payments are omitted as allowed in the brief.

## Three layers

1. Presentation: HTML forms and tables; CSS controls appearance.
2. Application: Flask receives requests, validates fields, and coordinates operations.
3. Data: MySQL stores tables and enforces keys/constraints. InnoDB handles transactions and locking.

POST changes data. GET retrieves pages. After a successful POST, Flask redirects to a GET page to reduce accidental browser resubmission.

## Data dictionary

See schema.sql for every exact type, default, enum value, and constraint.

| Table | Attributes |
|---|---|
| customer | CustomerID INT PK; FirstName/LastName VARCHAR(60); DateOfBirth DATE; Gender ENUM; Mobile VARCHAR(20); Email VARCHAR(120) UNIQUE; Address VARCHAR(255); City VARCHAR(80); RegistrationDate DATE |
| branch | BranchID INT PK; BranchName VARCHAR(100); IFSCCode VARCHAR(11) UNIQUE; Address VARCHAR(255); City/State VARCHAR(80); ContactNumber VARCHAR(20) |
| employee | EmployeeID INT PK; EmployeeName VARCHAR(120); Mobile VARCHAR(20); Email VARCHAR(120) UNIQUE; Designation VARCHAR(60); Salary DECIMAL(12,2); JoiningDate DATE; BranchID INT FK |
| account | AccountID INT PK; AccountNumber VARCHAR(24) UNIQUE; AccountType ENUM; OpeningDate DATE; Balance DECIMAL(15,2); Status ENUM; BranchID INT FK |
| account_holder | CustomerID INT PK/FK; AccountID INT PK/FK; HolderSince DATE; HolderType ENUM |
| bank_transaction | TransactionID BIGINT PK; AccountID INT FK; TransactionType ENUM; Amount DECIMAL(15,2); TransactionDate DATETIME; Description VARCHAR(255); ReferenceNumber VARCHAR(40); TransactionStatus ENUM |
| balance_audit | AuditID BIGINT PK; AccountID INT FK; OldBalance/NewBalance DECIMAL(15,2); ChangedAt DATETIME |

Phone/account numbers are text identifiers, not quantities. DECIMAL is used for exact decimal money arithmetic; Python uses Decimal rather than float for the same reason.

## Relationships and cardinality

| Parent → child | Relationship | Minimum/maximum |
|---|---|---|
| branch → employee | 1:M | Branch has 0..many employees; employee has exactly 1 branch |
| branch → account | 1:M | Branch has 0..many accounts; account has exactly 1 branch |
| customer → account_holder | 1:M | Registered customer has 0..many holder rows; each row has exactly 1 customer |
| account → account_holder | 1:M | Account should have 1..many holders; each row has exactly 1 account |
| account → bank_transaction | 1:M | Account has 0..many entries; entry belongs to exactly 1 account |
| account → balance_audit | 1:M | Account has 0..many audit records; each record belongs to exactly 1 account |

Customer ↔ account is M:N through account_holder. The composite primary key prevents adding the same customer to the same account twice. Foreign keys alone cannot enforce that every account has a holder: the application creates account + holder rows in one transaction. Direct manual SQL can bypass that business rule. The primary holder is chosen by lowest selected customer ID in this simplified app; it is not a legal ownership distinction.

## Keys and integrity

- Entity: an object being modeled, such as Customer or Branch.
- Attribute: a property, such as Email or Balance.
- Primary key: unique, non-null row identifier.
- Candidate key: a minimal set of attributes that can uniquely identify a row. CustomerID and the required unique Email are candidate keys in this model.
- Foreign key: references a key in another table to maintain referential integrity.
- Composite key: a key containing multiple columns, as in account_holder.
- Superkey: any set that uniquely identifies a row, possibly including unnecessary attributes.
- UNIQUE: prevents duplicate values; NOT NULL: requires a value; CHECK: restricts allowed values.
- Entity integrity: primary keys are unique and non-null.
- Referential integrity: child references point to existing parents.
- Domain integrity: data types, enums, and checks restrict values.

## Normalization

- 1NF: atomic values, no repeating lists of account IDs inside a customer row. Holders have separate rows.
- 2NF: each non-key attribute depends on the whole candidate key. In account_holder, HolderSince and HolderType describe that customer/account association.
- 3NF: no non-key-to-non-key dependencies in the intended model. Branch address is stored in branch, not repeated in every account/employee.

Balance is deliberately stored for fast reads and reconciled against the ledger. This is redundant aggregate data, maintained by application transactions; normalization by itself does not guarantee those two values stay consistent.

## Important DBMS objects

- Join: combines related rows, for example account → account_holder → customer.
- INNER JOIN: returns matching rows. LEFT JOIN retains parents that have no children.
- View: named SELECT; account_details has one row per account-holder pair. A joint account appears multiple times, so do not SUM balances from this view to calculate bank totals.
- Stored procedure: named database routine invoked with CALL. GetCustomerAccounts returns an account-details result set for one customer.
- Stored function: returns a scalar value in a query. CustomerTotalBalance returns full balances of accounts held by that customer. It is NOT DETERMINISTIC because table contents change.
- Trigger: automatic action on a table event. audit_balance_change records old/new balances after UPDATE. Audit changes roll back with their parent operation.
- Transaction: a group of changes committed or rolled back together.
- Index: lookup structure. The account/date index helps history lookup; unique keys also create indexes.

## ACID in this application

- Atomicity: debit, credit, and both transfer entries succeed together or none persists.
- Consistency: application checks plus database constraints preserve intended rules when all writers follow the design.
- Isolation: FOR UPDATE locks the account rows; concurrent operations on the same accounts must wait rather than read and overwrite the same balance.
- Durability: committed changes are retained by MySQL according to its storage/durability configuration.

## Money workflow

Form → CSRF validation → field validation → BEGIN → lock rows → check active status and funds → UPDATE balances → INSERT positive-amount ledger entries → audit trigger records changes → COMMIT → redirect → history.

Any exception in the transaction block calls ROLLBACK. Transfer locks happen in ascending account ID order to reduce deadlock risk. A unique UUID reference and transaction type reject duplicate submissions. In a transfer, the outgoing and incoming entries use different types and share the reference.

Only the application changes Balance; the trigger records an audit. Updating Balance in both a trigger and Python would apply the change twice.

