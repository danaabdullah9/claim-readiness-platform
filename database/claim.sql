-- CREATE TABLE Providers (
--     ProviderID INTEGER PRIMARY KEY AUTOINCREMENT,
--     ProviderName TEXT NOT NULL,
--     ProviderType TEXT NOT NULL,
--     City TEXT,
--     PhoneNumber TEXT
-- );


-- CREATE TABLE Diagnoses (
--     DiagnosisID INTEGER PRIMARY KEY AUTOINCREMENT,
--     DiagnosisCode TEXT NOT NULL UNIQUE,
--     DiagnosisDescription TEXT NOT NULL
-- );


-- CREATE TABLE Claims (
--     ClaimID INTEGER PRIMARY KEY AUTOINCREMENT,

--     UserID INTEGER NOT NULL,
--     ProviderID INTEGER NOT NULL,
--     DiagnosisID INTEGER NOT NULL,

--     InvoiceNumber TEXT NOT NULL UNIQUE,
--     InvoiceDate DATE NOT NULL,

--     DoctorName TEXT NOT NULL,

--     TotalAmount DECIMAL(10,2) NOT NULL,

--     ClinicalSummary TEXT,

--     ClaimStatus TEXT NOT NULL DEFAULT 'Pending'
--         CHECK (ClaimStatus IN ('Pending', 'Approved', 'Rejected')),

--     CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,

--     FOREIGN KEY (UserID) REFERENCES Users(UserID),
--     FOREIGN KEY (ProviderID) REFERENCES Providers(ProviderID),
--     FOREIGN KEY (DiagnosisID) REFERENCES Diagnoses(DiagnosisID)
-- );


-- CREATE TABLE Documents (
--     DocumentID INTEGER PRIMARY KEY AUTOINCREMENT,

--     ClaimID INTEGER NOT NULL,

--     DocumentType TEXT NOT NULL
--         CHECK (DocumentType IN ('Invoice', 'Medical Report', 'Prescription', 'Other')),

--     FileName TEXT NOT NULL,

--     UploadDate DATETIME DEFAULT CURRENT_TIMESTAMP,

--     FOREIGN KEY (ClaimID) REFERENCES Claims(ClaimID)
-- );




-- INSERT INTO Users (
--     Name,
--     Email,
--     PhoneNumber,
--     IdentityNumber,
--     Password
-- )
-- VALUES (
--     'Ahmed Ali',
--     'ahmed.ali@example.com',
--     '0501234567',
--     '1023456789',
--     'password123'
-- );


-- INSERT INTO Providers (
--     ProviderName,
--     ProviderType,
--     City,
--     PhoneNumber
-- )
-- VALUES (
--     'King Faisal Hospital',
--     'Hospital',
--     'Jeddah',
--     '0126543210'
-- );


-- INSERT INTO Diagnoses (
--     DiagnosisCode,
--     DiagnosisDescription
-- )
-- VALUES (
--     'J06.9',
--     'Acute upper respiratory infection'
-- );


-- INSERT INTO Claims (
--     UserID,
--     ProviderID,
--     DiagnosisID,
--     InvoiceNumber,
--     InvoiceDate,
--     DoctorName,
--     TotalAmount,
--     ClinicalSummary,
--     ClaimStatus
-- )
-- VALUES (
--     1,
--     1,
--     1,
--     'INV-2026-0001',
--     '2026-07-28',
--     'Dr. Sarah Hassan',
--     850.00,
--     'Patient complained of fever, sore throat, and cough. Prescribed antibiotics and advised to rest.',
--     'Pending'
-- );


-- INSERT INTO Documents (
--     ClaimID,
--     DocumentType,
--     FileName
-- )
-- VALUES (
--     1,
--     'Invoice',
--     'invoice_0001.pdf'
-- );





-- CREATE TABLE Employees (
--     EmployeeID INTEGER PRIMARY KEY AUTOINCREMENT,
--     FullName TEXT NOT NULL,
--     Email TEXT NOT NULL UNIQUE,
--     Password TEXT NOT NULL,
--     IsActive INTEGER NOT NULL DEFAULT 1
--         CHECK (IsActive IN (0,1))
-- );


-- INSERT INTO Employees (
--     FullName,
--     Email,
--     Password,
--     IsActive
-- )
-- VALUES (
--     'Sarah Ahmed',
--     'sarah.ahmed@insurance.com',
--     'password123',
--     1
-- );

-- INSERT INTO Employees (
--     FullName,
--     Email,
--     Password,
--     IsActive
-- )
-- VALUES (
--     'Mohammed Alharbi',
--     'mohammed.alharbi@insurance.com',
--     'password456',
--     1
-- );





-- SELECT * FROM Users;

-- SELECT * FROM Providers;

-- SELECT * FROM Diagnoses;

-- SELECT * FROM Claims;

-- SELECT * FROM Documents;

DELETE FROM Claims;
