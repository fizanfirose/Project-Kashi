-- Run SECOND. Adds fictional branches and employees only.
-- No hidden starting balances: register customers and deposit through the website.
USE project_kashi;
INSERT INTO branch (BranchName,IFSCCode,Address,City,State,ContactNumber)
SELECT 'Mangalore Central','KASH0000001','Demo College Road','Mangalore','Karnataka','0000000001'
WHERE NOT EXISTS (SELECT 1 FROM branch WHERE IFSCCode='KASH0000001');
INSERT INTO branch (BranchName,IFSCCode,Address,City,State,ContactNumber)
SELECT 'Kochi City','KASH0000002','Demo Market Road','Kochi','Kerala','0000000002'
WHERE NOT EXISTS (SELECT 1 FROM branch WHERE IFSCCode='KASH0000002');
INSERT INTO employee (EmployeeName,Mobile,Email,Designation,Salary,JoiningDate,BranchID)
SELECT 'Demo Manager','0000000003','manager@example.com','Branch Manager',50000,'2026-01-01',BranchID
FROM branch WHERE IFSCCode='KASH0000001'
AND NOT EXISTS (SELECT 1 FROM employee WHERE Email='manager@example.com');
INSERT INTO employee (EmployeeName,Mobile,Email,Designation,Salary,JoiningDate,BranchID)
SELECT 'Demo Teller','0000000004','teller@example.com','Teller',30000,'2026-01-01',BranchID
FROM branch WHERE IFSCCode='KASH0000002'
AND NOT EXISTS (SELECT 1 FROM employee WHERE Email='teller@example.com');
