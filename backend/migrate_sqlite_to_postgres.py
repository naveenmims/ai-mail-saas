import os
import sqlite3
from sqlalchemy import create_engine, text

SQLITE_PATH = "ai_mail.db"
PG_URL = os.environ["DATABASE_URL"]

engine = create_engine(PG_URL, future=True)

# Columns that are booleans in Postgres but may be 0/1 in SQLite
BOOL_COLS_BY_TABLE = {
    "organizations": {"auto_reply_enabled"},
}

def normalize(table: str, row: dict) -> dict:
    # Convert 0/1 -> True/False for known boolean columns
    bool_cols = BOOL_COLS_BY_TABLE.get(table, set())
    for c in bool_cols:
        if c in row and row[c] is not None:
            v = row[c]
            if isinstance(v, (int, float)):
                row[c] = bool(int(v))
            elif isinstance(v, str) and v.strip() in ("0", "1"):
                row[c] = bool(int(v.strip()))
    return row

def rows(sqlite_cur, table):
    sqlite_cur.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in sqlite_cur.description]
    for r in sqlite_cur.fetchall():
        d = dict(zip(cols, r))
        yield normalize(table, d)

def upsert(conn, table, row, pk="id"):
    cols = list(row.keys())
    placeholders = ", ".join([f":{c}" for c in cols])
    colnames = ", ".join(cols)

    # default: update all non-pk cols
    updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols if c != pk])

    # ✅ special-case reply_thread_locks unique key
    if table == "reply_thread_locks":
        conflict_cols = "org_id, thread_key"
        updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols if c not in ("org_id", "thread_key")])
    else:
        conflict_cols = pk

    sql = f"""
    INSERT INTO {table} ({colnames})
    VALUES ({placeholders})
    ON CONFLICT ({conflict_cols}) DO UPDATE SET
      {updates}
    """
    conn.execute(text(sql), row)

def main():
    if not os.path.exists(SQLITE_PATH):
        raise SystemExit(f"SQLite DB not found: {SQLITE_PATH}")

    sconn = sqlite3.connect(SQLITE_PATH)
    scur = sconn.cursor()

    tables = [
        "organizations",
        "email_accounts",
        "users",
        "org_credits",
        "org_usage",
        "reply_thread_locks",
        "conversation_audit",
    ]

    with engine.begin() as conn:
        for t in tables:
            try:
                count = scur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception as e:
                print(f"[SKIP] {t}: {e}")
                continue

            print(f"[MIGRATE] {t}: {count} rows")
            moved = 0
            for r in rows(scur, t):
                upsert(conn, t, r, pk="id")
                moved += 1
            print(f"  -> upserted {moved}")

    sconn.close()
    print("DONE")

if __name__ == "__main__":
    main()
