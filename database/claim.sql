

-- CREATING TABLES




-- new

-- CREATE TABLE Providers (
--     ProviderID INTEGER PRIMARY KEY AUTOINCREMENT,
--     ProviderCode TEXT UNIQUE,
--     ProviderName TEXT NOT NULL,
--     ProviderType TEXT,
--     ClinicType TEXT,
--     Department TEXT,
--     City TEXT,
--     PhoneNumber TEXT
-- );




-- CREATE TABLE Users (
--     user_ID INTEGER PRIMARY KEY AUTOINCREMENT,
--     Name TEXT NOT NULL,
--     NationalID TEXT NOT NULL UNIQUE,
--     Email TEXT NOT NULL UNIQUE,
--     Password TEXT NOT NULL,
--     MemberID TEXT NOT NULL UNIQUE,
--     File TEXT NOT NULL,
--     Gender TEXT NOT NULL,
--     Age INTEGER NOT NULL,
--     Nationality TEXT NOT NULL,
--     IBAN TEXT NOT NULL UNIQUE
-- );


-- CREATE TABLE Employees (
--     EmployeeID INTEGER PRIMARY KEY,
--     FullName TEXT NOT NULL,
--     IsActive INTEGER NOT NULL DEFAULT 1
--         CHECK (IsActive IN (0,1))
-- );


-- CREATE TABLE Diagnoses (
--     DiagnosisID INTEGER PRIMARY KEY AUTOINCREMENT,
--     DiagnosisCode TEXT NOT NULL UNIQUE,
--     DiagnosisDescription TEXT NOT NULL
-- );


-- CREATE TABLE Doctors (
--     DoctorID INTEGER PRIMARY KEY AUTOINCREMENT,
--     DoctorName TEXT NOT NULL,
--     Specialty TEXT,
--     ProviderID INTEGER NOT NULL,

--     FOREIGN KEY (ProviderID)
--         REFERENCES Providers(ProviderID)
-- );





-- CREATE TABLE Claims (
--     ClaimID INTEGER PRIMARY KEY AUTOINCREMENT,

--     ClaimNumber TEXT NOT NULL UNIQUE,

--     UserID INTEGER NOT NULL,
--     ProviderID INTEGER NOT NULL,
--     DoctorID INTEGER NOT NULL,
--     DiagnosisID INTEGER NOT NULL,

--     DoctorName TEXT,

--     ClaimType TEXT NOT NULL,
--     EpisodeNumber TEXT,

--     InsuranceCompany TEXT NOT NULL,
--     CompanyVAT TEXT,

--     InvoiceNumber TEXT NOT NULL UNIQUE,
--     InvoiceDate DATE NOT NULL,

--     ProcedureCode TEXT,
--     ServiceDescription TEXT,

--     Quantity INTEGER NOT NULL DEFAULT 1,
--     UnitPrice DECIMAL(10,2),
--     VAT DECIMAL(10,2),
--     TotalAmount DECIMAL(10,2) NOT NULL,

--     ClinicalSummary TEXT,
--     ChiefComplaint TEXT,
--     MedicalHistory TEXT,
--     Examination TEXT,
--     TreatmentPlan TEXT,
--     Medications TEXT,

--     ClaimStatus TEXT NOT NULL DEFAULT 'Pending'
--         CHECK (ClaimStatus IN ('Pending', 'Approved', 'Rejected')),

--     CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,

--     FOREIGN KEY (UserID)
--         REFERENCES Users(user_ID),

--     FOREIGN KEY (ProviderID)
--         REFERENCES Providers(ProviderID),

--     FOREIGN KEY (DoctorID)
--         REFERENCES Doctors(DoctorID),

--     FOREIGN KEY (DiagnosisID)
--         REFERENCES Diagnoses(DiagnosisID)
-- );


-- CREATE TABLE Documents (
--     DocumentID INTEGER PRIMARY KEY AUTOINCREMENT,

--     ClaimID INTEGER NOT NULL,

--     DocumentType TEXT NOT NULL
--         CHECK (DocumentType IN
--         ('Invoice',
--          'Medical Report',
--          'Prescription',
--          'Other')),

--     FileName TEXT NOT NULL,

--     UploadDate DATETIME DEFAULT CURRENT_TIMESTAMP,

--     FOREIGN KEY (ClaimID)
--         REFERENCES Claims(ClaimID)
-- );






-- INSERTING INTO TABLES





-- INSERT INTO Employees (EmployeeID, FullName, IsActive)
-- VALUES
-- (1001, 'Noura Alharbi', 1),
-- (1002, 'Mohammed Alotaibi', 1),
-- (1003, 'Sara Alshammari', 1);



-- INSERT INTO Users
-- (Name, NationalID, Email, Password, MemberID, File, Gender, Age, Nationality, IBAN)
-- VALUES
-- ('Ahmed Ali',
--  '1120400591',
--  'ahmed.ali@example.com',
--  'Ahmed123',
--  'BP12345',
--  '30026571',
--  'Male',
--  34,
--  'Saudi',
--  'SA0380000000608010167519'),

-- ('Fatimah Nasser',
--  '1099230145',
--  'fatimah.nasser@example.com',
--  'Fatimah123',
--  'BP22981',
--  '30041882',
--  'Female',
--  29,
--  'Saudi',
--  'SA4420000001234567890123'),

-- ('Sara Mahmoud',
--  '2455677812',
--  'sara.mahmoud@example.com',
--  'Sara123',
--  'BP61203',
--  '30084011',
--  'Female',
--  31,
--  'Jordanian',
--  'SA6820000009876543210987');



--  VIEWING TABLES




-- SELECT * FROM Users;

-- SELECT * FROM Providers;

-- SELECT * FROM Diagnoses;

-- SELECT * FROM Claims;

-- SELECT * FROM Documents;

-- SELECT * FROM Employees;

-- SELECT * FROM Doctors;
 

 







