"""Atomic shared credit accounting. Unknown balances/pending usage fail closed.

Use ONE database for all spenders (including BoundForge/forecasting). Copying this
database gives no additional spending rights. A remote deployment must provide an
equivalent transactional shared coordinator; an app-local SQLite is insufficient.
"""
import contextlib,datetime,json,sqlite3,time,uuid
class BudgetUnavailable(RuntimeError):pass
class Ledger:
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=30,isolation_level=None)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS providers(
          name TEXT PRIMARY KEY,unit TEXT NOT NULL,balance REAL,pending_external REAL,
          verification_reserve REAL NOT NULL,observed_at REAL NOT NULL,
          expires_at REAL NOT NULL,coordination_confirmed INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS reservations(
          id TEXT PRIMARY KEY,provider TEXT NOT NULL,project TEXT NOT NULL,
          reserved REAL NOT NULL,actual REAL,status TEXT NOT NULL,created_at REAL NOT NULL);
        """)
    def reserve(self,provider,project,amount):
        if amount<=0:raise ValueError("positive upper-bound reservation required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row=self.db.execute("SELECT balance,pending_external,verification_reserve,expires_at,coordination_confirmed FROM providers WHERE name=?",(provider,)).fetchone()
            if not row or row[0] is None or row[1] is None or not row[4] or time.time()>row[3]:
                raise BudgetUnavailable("Unknown/stale balance, external reservations, or shared coordination")
            spent=self.db.execute("SELECT COALESCE(SUM(CASE WHEN status='settled' THEN actual ELSE reserved END),0) FROM reservations WHERE provider=? AND status!='cancelled'",(provider,)).fetchone()[0]
            if row[0]-row[1]-row[2]-spent<amount:raise BudgetUnavailable("Existing credits insufficient after shared and verification reserves")
            identifier=str(uuid.uuid4())
            self.db.execute("INSERT INTO reservations VALUES(?,?,?,?,NULL,'pending',?)",(identifier,provider,project,amount,time.time()))
            self.db.execute("COMMIT");return identifier
        except Exception:self.db.execute("ROLLBACK");raise
    def settle(self,identifier,actual):
        if actual is None:return # unknown provider usage retains full reservation
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row=self.db.execute("SELECT reserved,status FROM reservations WHERE id=?",(identifier,)).fetchone()
            if not row or row[1]!="pending":raise ValueError("unknown or closed reservation")
            if actual<0 or actual>row[0]:raise BudgetUnavailable("Provider charge exceeds reserved upper bound; stop provider")
            self.db.execute("UPDATE reservations SET actual=?,status='settled' WHERE id=?",(actual,identifier));self.db.execute("COMMIT")
        except Exception:self.db.execute("ROLLBACK");raise
