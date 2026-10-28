USE project_kashi;

-- 1. Customers in Mangalore.
SELECT CustomerID,FirstName,LastName,Mobile FROM customer WHERE City='Mangalore';

-- 2. Active accounts held by customer 1.
SELECT a.* FROM account a JOIN account_holder h ON a.AccountID=h.AccountID
WHERE h.CustomerID=1 AND a.Status='Active';

-- 3. Customers with more than one account.
SELECT c.CustomerID,c.FirstName,c.LastName,COUNT(*) AS AccountCount
FROM customer c JOIN account_holder h ON c.CustomerID=h.CustomerID
GROUP BY c.CustomerID,c.FirstName,c.LastName HAVING COUNT(*)>1;

-- 4. Joint accounts (more than one holder).
SELECT a.AccountNumber,COUNT(*) AS HolderCount FROM account a
JOIN account_holder h ON a.AccountID=h.AccountID
GROUP BY a.AccountID,a.AccountNumber HAVING COUNT(*)>1;

-- 5. Account count per branch (including branches with zero accounts).
SELECT b.BranchName,COUNT(a.AccountID) AS AccountCount FROM branch b
LEFT JOIN account a ON a.BranchID=b.BranchID GROUP BY b.BranchID,b.BranchName;

-- 6. Total balance per branch, without duplicating joint accounts.
SELECT b.BranchName,COALESCE(SUM(a.Balance),0) AS TotalBalance FROM branch b
LEFT JOIN account a ON a.BranchID=b.BranchID GROUP BY b.BranchID,b.BranchName;

-- 7. Accounts above INR 5,000.
SELECT AccountNumber,Balance FROM account WHERE Balance>5000 ORDER BY Balance DESC;

-- 8. Latest 10 entries for account ID 1.
SELECT * FROM bank_transaction WHERE AccountID=1
ORDER BY TransactionDate DESC,TransactionID DESC LIMIT 10;

-- 9. Total cash deposited today (transfers are excluded).
SELECT COALESCE(SUM(Amount),0) AS DepositedToday FROM bank_transaction
WHERE TransactionType='DEPOSIT' AND DATE(TransactionDate)=CURRENT_DATE();

-- 10. Accounts without any transaction history.
SELECT a.AccountNumber FROM account a WHERE NOT EXISTS
(SELECT 1 FROM bank_transaction t WHERE t.AccountID=a.AccountID);

-- 11. Employee salary costs by branch.
SELECT b.BranchName,COALESCE(SUM(e.Salary),0) AS SalaryCost FROM branch b
LEFT JOIN employee e ON e.BranchID=b.BranchID GROUP BY b.BranchID,b.BranchName;

-- 12. Ledger reconciliation: expected zero rows when every account began at zero
-- and all balance changes went through this app.
SELECT a.AccountNumber,a.Balance,COALESCE(SUM(CASE
 WHEN t.TransactionType IN ('DEPOSIT','TRANSFER_IN') THEN t.Amount
 ELSE -t.Amount END),0) AS LedgerBalance
FROM account a LEFT JOIN bank_transaction t ON t.AccountID=a.AccountID
GROUP BY a.AccountID,a.AccountNumber,a.Balance HAVING a.Balance<>LedgerBalance;
