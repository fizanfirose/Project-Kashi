-- Run THIRD. Select all, then execute the whole script in Workbench.
USE project_kashi;

CREATE OR REPLACE VIEW account_details AS
SELECT a.AccountID,a.AccountNumber,a.AccountType,a.Balance,a.Status,
 b.BranchName,c.CustomerID,CONCAT(c.FirstName,' ',c.LastName) AS CustomerName,h.HolderType
FROM account a JOIN branch b ON a.BranchID=b.BranchID
JOIN account_holder h ON a.AccountID=h.AccountID
JOIN customer c ON c.CustomerID=h.CustomerID;

DROP PROCEDURE IF EXISTS GetCustomerAccounts;
DROP FUNCTION IF EXISTS CustomerTotalBalance;
DROP TRIGGER IF EXISTS audit_balance_change;

DELIMITER $$
CREATE PROCEDURE GetCustomerAccounts(IN p_customer_id INT)
READS SQL DATA
BEGIN
 SELECT * FROM account_details WHERE CustomerID=p_customer_id;
END$$

CREATE FUNCTION CustomerTotalBalance(p_customer_id INT)
RETURNS DECIMAL(15,2)
NOT DETERMINISTIC
READS SQL DATA
BEGIN
 DECLARE result DECIMAL(15,2);
 SELECT COALESCE(SUM(a.Balance),0) INTO result
 FROM account a JOIN account_holder h ON a.AccountID=h.AccountID
 WHERE h.CustomerID=p_customer_id;
 RETURN result;
END$$

CREATE TRIGGER audit_balance_change AFTER UPDATE ON account
FOR EACH ROW
BEGIN
 IF OLD.Balance <> NEW.Balance THEN
  INSERT INTO balance_audit (AccountID,OldBalance,NewBalance)
  VALUES (NEW.AccountID,OLD.Balance,NEW.Balance);
 END IF;
END$$
DELIMITER ;

-- Demo after customer/account creation:
-- CALL GetCustomerAccounts(1);
-- SELECT CustomerTotalBalance(1);
-- SELECT * FROM balance_audit;
-- If CREATE FUNCTION gets error 1418/1419, read README troubleshooting.
