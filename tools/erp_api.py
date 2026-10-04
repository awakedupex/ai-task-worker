"""ERP tools: write directly to SQLite (reliable) + optional HTTP to mock server."""
import os
import re
import sqlite3
from tools.base import Tool, Observation

DB_PATH = os.getenv("ERP_DB_PATH", "mock_env/erp.db")


def _connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS invoices(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      vendor TEXT, amount REAL, due_date TEXT, source_file TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    return con


def create_entry(vendor, amount, due_date, source_file=""):
    if not vendor or amount is None or not due_date:
        raise ValueError(f"missing field vendor={vendor} amount={amount} due_date={due_date}")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(due_date)):
        raise ValueError(f"due_date must be YYYY-MM-DD, got {due_date}")
    amount = float(amount)
    con = _connect()
    cur = con.execute("INSERT INTO invoices(vendor,amount,due_date,source_file) VALUES(?,?,?,?)",
                      (vendor, amount, due_date, source_file))
    con.commit()
    eid = cur.lastrowid
    con.close()
    return eid


class ERPCreateTool(Tool):
    name = "erp_api.create"
    description = "Create an entry in the internal ERP system. Uses verified vendor/amount/due_date. Args may be empty: facts from memory are auto-filled by orchestrator."
    schema = {"type": "object", "properties": {
        "vendor": {"type": "string"}, "amount": {"type": "number"},
        "due_date": {"type": "string"}, "invoice_id": {"type": "string"}}}

    def execute(self, args):
        # args may be empty when MockLLM defers filling; caller (loop) pre-fills from memory.
        try:
            eid = create_entry(args.get("vendor"), args.get("amount"),
                               args.get("due_date"), args.get("invoice_id", ""))
            return Observation(ok=True, data={"erp_id": eid, "vendor": args.get("vendor"),
                                              "amount": args.get("amount"), "due_date": args.get("due_date")},
                               evidence={"erp_id": eid, "db": DB_PATH})
        except Exception as e:
            return Observation(ok=False, error=f"ERP create failed: {e}")


class ERPGetTool(Tool):
    name = "erp_api.get"
    description = "Fetch an ERP entry by id to verify it was stored."
    schema = {"type": "object", "properties": {"erp_id": {"type": "integer"}}, "required": ["erp_id"]}

    def execute(self, args):
        try:
            con = _connect()
            row = con.execute("SELECT id,vendor,amount,due_date,source_file FROM invoices WHERE id=?",
                              (args.get("erp_id"),)).fetchone()
            con.close()
            if not row:
                return Observation(ok=False, error=f"erp_id {args.get('erp_id')} not found")
            return Observation(ok=True, data={"erp_id": row[0], "vendor": row[1], "amount": row[2],
                                              "due_date": row[3], "source_file": row[4]})
        except Exception as e:
            return Observation(ok=False, error=str(e))


class ERPListTool(Tool):
    name = "erp_api.list"
    description = "List recent ERP entries (verification)."
    schema = {"type": "object", "properties": {"limit": {"type": "integer"}}}

    def execute(self, args):
        try:
            con = _connect()
            rows = con.execute("SELECT id,vendor,amount,due_date FROM invoices ORDER BY id DESC LIMIT ?",
                               (int(args.get("limit") or 5),)).fetchall()
            con.close()
            return Observation(ok=True, data={"entries": [
                {"erp_id": r[0], "vendor": r[1], "amount": r[2], "due_date": r[3]} for r in rows]})
        except Exception as e:
            return Observation(ok=False, error=str(e))
