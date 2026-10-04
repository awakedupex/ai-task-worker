"""Mock internal ERP: REST API + minimal HTML UI (for browser tool). Run: uvicorn mock_env.erp_server:app --port 8000"""
import os
import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

DB = os.path.join(os.path.dirname(__file__), "erp.db")
app = FastAPI(title="Mock Company ERP")


def _con():
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS invoices(
      id INTEGER PRIMARY KEY AUTOINCREMENT, vendor TEXT, amount REAL,
      due_date TEXT, source_file TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    return con


class InvoiceIn(BaseModel):
    vendor: str
    amount: float
    due_date: str
    source_file: str = ""


@app.post("/api/invoices")
def create(inv: InvoiceIn):
    con = _con()
    cur = con.execute("INSERT INTO invoices(vendor,amount,due_date,source_file) VALUES(?,?,?,?)",
                      (inv.vendor, inv.amount, inv.due_date, inv.source_file))
    con.commit()
    eid = cur.lastrowid
    con.close()
    return {"id": eid, **inv.dict()}


@app.get("/api/invoices")
def list_invoices(limit: int = 20):
    con = _con()
    rows = con.execute("SELECT id,vendor,amount,due_date,source_file FROM invoices ORDER BY id DESC LIMIT ?",
                       (limit,)).fetchall()
    con.close()
    return [{"id": r[0], "vendor": r[1], "amount": r[2], "due_date": r[3], "source_file": r[4]} for r in rows]


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """<html><head><title>Mock ERP - Enter Invoice</title></head><body>
<h2>Mock ERP - Enter Invoice</h2>
<form method="post" action="/ui/submit">
<label>Vendor <input id="vendor" name="vendor"/></label><br/>
<label>Amount <input id="amount" name="amount"/></label><br/>
<label>Due (YYYY-MM-DD) <input id="due" name="due_date"/></label><br/>
<button id="submit" type="submit">Submit</button>
</form></body></html>"""
