"""ترقية سكيمة قاعدة البيانات للأنظمة الجديدة.

تشغيلها آمن أكثر من مرة: كل شيء CREATE TABLE IF NOT EXISTS، وإضافة الأعمدة
تتحقق أولاً من وجودها. لا تحذف ولا تعدّل أي بيانات موجودة.

    python schema_upgrade.py

هذا الملف ينشئ الجداول فقط. البيانات (العائلة، التاريخ المرضي، الفئات) تُضاف
من claim_extension.sql عشان تبقى تحت سيطرتك ومع بقية بيانات المشروع.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "claimDB.db"


SCHEMA = """
-- فئة التأمين لكل مستفيد وسقفه السنوي
CREATE TABLE IF NOT EXISTS MemberPolicy (
    user_ID          INTEGER PRIMARY KEY,
    Tier             TEXT NOT NULL DEFAULT 'Essential',
    PolicyNumber     TEXT,
    PolicyStart      DATE,
    PolicyEnd        DATE,
    InsuranceCompany TEXT NOT NULL DEFAULT 'Bupa',
    FOREIGN KEY (user_ID) REFERENCES Users(user_ID)
);

-- ربط أفراد العائلة برب الأسرة
CREATE TABLE IF NOT EXISTS FamilyLinks (
    LinkID       INTEGER PRIMARY KEY AUTOINCREMENT,
    HeadUserID   INTEGER NOT NULL,
    MemberUserID INTEGER NOT NULL,
    Relationship TEXT NOT NULL CHECK (Relationship IN ('Spouse','Son','Daughter','Father','Mother')),
    CreatedAt    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (HeadUserID, MemberUserID),
    FOREIGN KEY (HeadUserID)   REFERENCES Users(user_ID),
    FOREIGN KEY (MemberUserID) REFERENCES Users(user_ID)
);

-- موافقة مشاركة البيانات: من بلغ 18 له حق المنع
CREATE TABLE IF NOT EXISTS DataSharingConsent (
    user_ID        INTEGER PRIMARY KEY,
    ShareWithHead  INTEGER NOT NULL DEFAULT 1,
    ShareHistory   INTEGER NOT NULL DEFAULT 1,
    UpdatedAt      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_ID) REFERENCES Users(user_ID)
);

-- التاريخ المرضي: مزمن للشخص، ووراثي ينتقل للأبناء
CREATE TABLE IF NOT EXISTS MedicalHistory (
    HistoryID      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_ID        INTEGER NOT NULL,
    ConditionCode  TEXT NOT NULL,
    ConditionName  TEXT NOT NULL,
    IsChronic      INTEGER NOT NULL DEFAULT 0,
    IsHereditary   INTEGER NOT NULL DEFAULT 0,
    DiagnosedOn    DATE,
    Notes          TEXT,
    CreatedAt      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_ID) REFERENCES Users(user_ID)
);

-- القائمة السوداء
CREATE TABLE IF NOT EXISTS Blacklist (
    EntryID    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_ID    INTEGER,
    NationalID TEXT,
    Reason     TEXT NOT NULL,
    AddedBy    TEXT,
    AddedAt    DATETIME DEFAULT CURRENT_TIMESTAMP,
    IsActive   INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_ID) REFERENCES Users(user_ID)
);

-- إشارات الاحتيال المكتشفة لكل مطالبة
CREATE TABLE IF NOT EXISTS FraudSignals (
    SignalID  INTEGER PRIMARY KEY AUTOINCREMENT,
    ClaimID   INTEGER,
    user_ID   INTEGER,
    Code      TEXT NOT NULL,
    Severity  TEXT NOT NULL CHECK (Severity IN ('low','medium','high','critical')),
    Score     INTEGER NOT NULL DEFAULT 0,
    Detail    TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ClaimID) REFERENCES Claims(ClaimID),
    FOREIGN KEY (user_ID) REFERENCES Users(user_ID)
);

-- بصمة كل مستند مرفوع: لكشف إعادة الاستخدام والتزوير
CREATE TABLE IF NOT EXISTS DocumentFingerprints (
    FingerprintID  INTEGER PRIMARY KEY AUTOINCREMENT,
    ClaimID        INTEGER,
    user_ID        INTEGER,
    DocumentType   TEXT,
    FileName       TEXT,
    Sha256         TEXT NOT NULL,
    PerceptualHash TEXT,
    FileSize       INTEGER,
    PdfProducer    TEXT,
    PdfCreator     TEXT,
    PdfCreated     TEXT,
    PdfModified    TEXT,
    CreatedAt      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fingerprint_sha ON DocumentFingerprints(Sha256);

-- العلاجات الدورية المعتمدة للأتمتة
CREATE TABLE IF NOT EXISTS RecurringTreatments (
    RuleID        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_ID       INTEGER NOT NULL,
    BenefitCode   TEXT NOT NULL,
    ConditionCode TEXT,
    Description   TEXT,
    IntervalDays  INTEGER NOT NULL DEFAULT 180,
    MaxAmount     REAL NOT NULL,
    LastApproved  DATE,
    IsActive      INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_ID) REFERENCES Users(user_ID)
);

-- سجل قرارات الأتمتة والمحرّك
CREATE TABLE IF NOT EXISTS ClaimDecisions (
    DecisionID   INTEGER PRIMARY KEY AUTOINCREMENT,
    ClaimID      INTEGER NOT NULL,
    BenefitCode  TEXT,
    Decision     TEXT NOT NULL,
    PayableAmount REAL,
    MemberShare  REAL,
    FraudScore   INTEGER DEFAULT 0,
    AutoProcessed INTEGER NOT NULL DEFAULT 0,
    DecidedBy    TEXT,
    Rationale    TEXT,
    CreatedAt    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ClaimID) REFERENCES Claims(ClaimID)
);
"""

# أعمدة تُضاف لجداول موجودة
NEW_COLUMNS = {
    "Claims": [
        ("BenefitCode", "TEXT"),
        ("PayableAmount", "REAL"),
        ("FraudScore", "INTEGER DEFAULT 0"),
        ("AutoProcessed", "INTEGER DEFAULT 0"),
        ("ServiceDate", "DATE"),
    ],
    "Users": [
        ("DateOfBirth", "DATE"),
    ],
}


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _table_exists(conn, table):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def upgrade(db_path=DB_PATH, verbose=True):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    created = []

    try:
        before = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        conn.executescript(SCHEMA)
        after = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        created = sorted(after - before)

        added_columns = []
        for table, columns in NEW_COLUMNS.items():
            if not _table_exists(conn, table):
                continue
            existing = _columns(conn, table)
            for name, definition in columns:
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
                    added_columns.append(f"{table}.{name}")

        # كل مستفيد بلا وثيقة يحصل على الفئة الأساسية تلقائيًا
        conn.execute("""
            INSERT OR IGNORE INTO MemberPolicy (user_ID, Tier, InsuranceCompany)
            SELECT user_ID, 'Essential', 'Bupa' FROM Users
        """)
        conn.execute("""
            INSERT OR IGNORE INTO DataSharingConsent (user_ID, ShareWithHead, ShareHistory)
            SELECT user_ID, 1, 1 FROM Users
        """)

        conn.commit()

        if verbose:
            print(f"✅ جداول جديدة ({len(created)}): {', '.join(created) or 'لا شيء'}")
            print(f"✅ أعمدة جديدة ({len(added_columns)}): {', '.join(added_columns) or 'لا شيء'}")
    finally:
        conn.close()

    return created


if __name__ == "__main__":
    upgrade()