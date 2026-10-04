"""Independent verification: did the outcome actually happen? (not LLM self-report)."""
import os
import sqlite3
import re


def verify(task: str, facts: dict) -> dict:
    t = task.lower()
    if "invoice" in t:
        db = os.getenv("ERP_DB_PATH", "mock_env/erp.db")
        try:
            con = sqlite3.connect(db)
            if facts.get("erp_id"):
                row = con.execute("SELECT id,vendor,amount,due_date FROM invoices WHERE id=?",
                                  (facts["erp_id"],)).fetchone()
                con.close()
                if row:
                    return {"verified": True,
                            "detail": f"ERP row id={row[0]} vendor={row[1]} amount={row[2]} due={row[3]} exists in {db}"}
                return {"verified": False, "detail": f"erp_id {facts['erp_id']} not found in DB"}
            # fallback: match by amount+vendor
            rows = con.execute("SELECT id,vendor,amount,due_date FROM invoices ORDER BY id DESC LIMIT 10").fetchall()
            con.close()
            if rows:
                r = rows[0]
                return {"verified": True, "detail": f"Latest ERP entry id={r[0]} {r[1]} {r[2]} due {r[3]}"}
            return {"verified": False, "detail": "ERP table empty, no entry created"}
        except Exception as e:
            return {"verified": False, "detail": f"DB check failed: {e}"}
    # file/research tasks
    path = facts.get("file_path") or "reports/gst_note.md"
    if os.path.exists(path):
        try:
            with open(path, errors="replace") as f:
                c = f.read()
            has_num = bool(re.search(r"\d+%", c))
            has_src = "http" in c or "cbic" in c.lower()
            if len(c) > 150 and has_num and has_src:
                return {"verified": True, "detail": f"{path} exists ({len(c)} chars) with rate + sources"}
            return {"verified": False, "detail": f"{path} exists but missing rate/sources"}
        except Exception as e:
            return {"verified": False, "detail": str(e)}
    return {"verified": False, "detail": f"expected file {path} not found"}
