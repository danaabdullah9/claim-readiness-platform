"""تصفير بيانات الاختبار.

حذف جدول Claims وحده لا يكفي: بيانات المطالبة موزّعة على تسعة جداول وملفات
على القرص. البصمات والإشارات والقائمة السوداء تبقى وتؤثر على أي مطالبة جديدة،
فيظهر للموظف "مطالبة مكررة من #8" و #8 لم تعد موجودة أصلًا.

    python reset_claims.py                # يمسح المطالبات ويُبقي القائمة السوداء
    python reset_claims.py --all          # يمسح كل شيء بما فيه القائمة السوداء
    python reset_claims.py --status       # يعرض الحالة فقط بدون حذف

لا يُمسّ أبدًا: Users, Employees, MemberPolicy, FamilyLinks, DataSharingConsent,
MedicalHistory, RecurringTreatments.
"""

import shutil
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "claimDB.db"
UPLOADS_DIR = BASE_DIR / "database" / "claim_uploads"
CORRECTIONS_PATH = BASE_DIR / "database" / "user_corrections.json"

# جداول تُمسح دائمًا مع المطالبات
CLAIM_TABLES = [
    "ClaimDecisions",
    "FraudSignals",
    "DocumentFingerprints",
    "ClaimNotifications",
    "ClaimDocumentFiles",
    "Documents",
    "Claims",
]

# تُمسح فقط مع --all
EXTRA_TABLES = ["Blacklist"]

# جداول مرجعية يملؤها النظام تلقائيًا من المستندات
LOOKUP_TABLES = ["Providers", "Diagnoses", "Doctors"]


def _exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _count(conn, table):
    if not _exists(conn, table):
        return None
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def status(conn):
    print("الحالة الحالية:\n")
    for table in CLAIM_TABLES + EXTRA_TABLES + LOOKUP_TABLES:
        count = _count(conn, table)
        if count is not None:
            print(f"  {table:24} {count}")

    print("\n  يُحتفظ بها:")
    for table in ("Users", "Employees", "MemberPolicy", "FamilyLinks",
                  "DataSharingConsent", "MedicalHistory", "RecurringTreatments"):
        count = _count(conn, table)
        if count is not None:
            print(f"  {table:24} {count}")

    files = len(list(UPLOADS_DIR.rglob("*"))) if UPLOADS_DIR.exists() else 0
    print(f"\n  ملفات مرفوعة على القرص: {files}")


def reset(conn, include_blacklist=False, clear_lookups=True):
    tables = list(CLAIM_TABLES)
    if include_blacklist:
        tables += EXTRA_TABLES

    deleted = {}
    conn.execute("PRAGMA foreign_keys = OFF")

    for table in tables:
        if not _exists(conn, table):
            continue
        before = _count(conn, table)
        conn.execute(f"DELETE FROM {table}")
        deleted[table] = before

    if clear_lookups:
        # هذي الجداول يملؤها النظام من المستندات، وبقاؤها يخلي مطالبة جديدة
        # تعيد استخدام ProviderID قديم بدل إنشاء صف نظيف.
        for table in LOOKUP_TABLES:
            if _exists(conn, table):
                before = _count(conn, table)
                conn.execute(f"DELETE FROM {table}")
                deleted[table] = before

    # بدون هذا تكمل أرقام المطالبات من حيث توقفت (#9، #10...) رغم أن الجدول فارغ
    if _exists(conn, "sqlite_sequence"):
        placeholders = ",".join("?" for _ in tables + LOOKUP_TABLES)
        conn.execute(
            f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
            tables + LOOKUP_TABLES,
        )

    # العلاجات الدورية: نصفّر تاريخ آخر صرف فقط، والقاعدة نفسها تبقى
    if _exists(conn, "RecurringTreatments"):
        conn.execute("UPDATE RecurringTreatments SET LastApproved = NULL")

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")

    # الملفات المخزّنة على القرص
    removed_files = 0
    if UPLOADS_DIR.exists():
        removed_files = len([p for p in UPLOADS_DIR.rglob("*") if p.is_file()])
        shutil.rmtree(UPLOADS_DIR)
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    if CORRECTIONS_PATH.exists():
        CORRECTIONS_PATH.unlink()

    return deleted, removed_files


def main():
    if not DB_PATH.exists():
        print(f"❌ لم أجد قاعدة البيانات: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        if "--status" in sys.argv:
            status(conn)
            return 0

        include_blacklist = "--all" in sys.argv

        print("قبل التنظيف:")
        status(conn)
        print()

        deleted, removed_files = reset(conn, include_blacklist=include_blacklist)

        print("تم الحذف:")
        for table, count in deleted.items():
            if count:
                print(f"  {table:24} {count} صف")
        print(f"  ملفات على القرص        {removed_files}")

        if include_blacklist:
            print("\n✅ تصفير كامل — القائمة السوداء مُسحت أيضًا.")
        else:
            remaining = _count(conn, "Blacklist") or 0
            print(f"\n✅ تم. القائمة السوداء لم تُمسّ ({remaining} مُدرج).")
            if remaining:
                print("   لمسحها أيضًا: python reset_claims.py --all")

        print("\nلم تُمسّ: Users, Employees, MemberPolicy, FamilyLinks, "
              "DataSharingConsent, MedicalHistory, RecurringTreatments")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
