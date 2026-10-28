-- Run this FIRST in MySQL Workbench. Existing tables are preserved.
-- Requires MySQL 8.0.16+ for enforced CHECK constraints (MySQL 8.4 is suitable).
CREATE DATABASE IF NOT EXISTS project_kashi CHARACTER SET utf8mb4;
USE project_kashi;

CREATE TABLE IF NOT EXISTS branch (
 BranchID INT PRIMARY KEY AUTO_INCREMENT,
 BranchName VARCHAR(100) NOT NULL,
 IFSCCode VARCHAR(11) NOT NULL UNIQUE,
 Address VARCHAR(255) NOT NULL,
 City VARCHAR(80) NOT NULL,
 State VARCHAR(80) NOT NULL,
 ContactNumber VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS customer (
 CustomerID INT PRIMARY KEY AUTO_INCREMENT,
 FirstName VARCHAR(60) NOT NULL,
 LastName VARCHAR(60) NOT NULL,
 DateOfBirth DATE NOT NULL,
 Gender ENUM('Male','Female','Other','Prefer not to say') NOT NULL,
 Mobile VARCHAR(20) NOT NULL,
 Email VARCHAR(120) NOT NULL UNIQUE,
 Address VARCHAR(255) NOT NULL,
 City VARCHAR(80) NOT NULL,
 RegistrationDate DATE NOT NULL DEFAULT (CURRENT_DATE)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS employee (
 EmployeeID INT PRIMARY KEY AUTO_INCREMENT,
 EmployeeName VARCHAR(120) NOT NULL,
 Mobile VARCHAR(20) NOT NULL,
 Email VARCHAR(120) NOT NULL UNIQUE,
 Designation VARCHAR(60) NOT NULL,
 Salary DECIMAL(12,2) NOT NULL CHECK (Salary>=0),
 JoiningDate DATE NOT NULL,
 BranchID INT NOT NULL,
 FOREIGN KEY (BranchID) REFERENCES branch(BranchID)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS account (
 AccountID INT PRIMARY KEY AUTO_INCREMENT,
 AccountNumber VARCHAR(24) NOT NULL UNIQUE,
 AccountType ENUM('Saving','Current','Salary') NOT NULL,
 OpeningDate DATE NOT NULL DEFAULT (CURRENT_DATE),
 Balance DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK (Balance>=0),
 Status ENUM('Active','Inactive','Close') NOT NULL DEFAULT 'Active',
 BranchID INT NOT NULL,
 FOREIGN KEY (BranchID) REFERENCES branch(BranchID)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS account_holder (
 CustomerID INT NOT NULL,
 AccountID INT NOT NULL,
 HolderSince DATE NOT NULL DEFAULT (CURRENT_DATE),
 HolderType ENUM('Primary','Joint') NOT NULL DEFAULT 'Primary',
 PRIMARY KEY (CustomerID,AccountID),
 FOREIGN KEY (CustomerID) REFERENCES customer(CustomerID),
 FOREIGN KEY (AccountID) REFERENCES account(AccountID)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bank_transaction (
 TransactionID BIGINT PRIMARY KEY AUTO_INCREMENT,
 AccountID INT NOT NULL,
 TransactionType ENUM('DEPOSIT','WITHDRAWAL','TRANSFER_IN','TRANSFER_OUT') NOT NULL,
 Amount DECIMAL(15,2) NOT NULL CHECK (Amount>0),
 TransactionDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 Description VARCHAR(255),
 ReferenceNumber VARCHAR(40) NOT NULL,
 TransactionStatus ENUM('SUCCESS') NOT NULL DEFAULT 'SUCCESS',
 FOREIGN KEY (AccountID) REFERENCES account(AccountID),
 UNIQUE KEY uq_reference_direction (ReferenceNumber,TransactionType),
 INDEX idx_account_history (AccountID,TransactionDate)
) ENGINE=InnoDB;

-- Optional demonstration table used by the balance audit trigger.
CREATE TABLE IF NOT EXISTS balance_audit (
 AuditID BIGINT PRIMARY KEY AUTO_INCREMENT,
 AccountID INT NOT NULL,
 OldBalance DECIMAL(15,2) NOT NULL,
 NewBalance DECIMAL(15,2) NOT NULL,
 ChangedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (AccountID) REFERENCES account(AccountID)
) ENGINE=InnoDB;
