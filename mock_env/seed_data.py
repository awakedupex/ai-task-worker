"""Seed mock inbox with varied invoices (incl. edge cases) + init ERP DB."""
import os

INBOX = os.path.join(os.path.dirname(__file__), "inbox")

INVOICES = {
    "INV-Acme-2026-09-28.txt": """ACME CORP
Invoice INV-Acme-2026-09-28
Bill To: Our Company
Total: $4,820.50
Due: 2026-10-28
Thank you for your business.
""",
    "INV-Acme-2026-09-10.txt": """ACME CORP
Invoice INV-Acme-2026-09-10
Total: $3,150.00
Due: 2026-10-10
""",
    "INV-Globex-2026-09-25.txt": """GLOBEX INC
Invoice G-9921
Amount Due: $12,400.75
Due: 2026-10-15
""",
    "INV-Initech-2026-09-20.txt": """INITECH LLC
Invoice I-551
Grand Total: $980.00
Due: 20/10/2026
""",
    "INV-Acme-2026-08-30.txt": """ACME CORP
Invoice old
Total: $1,200.00
Due: 2026-09-30
""",
    "INV-Corrupt-2026-09-29.txt": """\x00\x01 CORRUPT BINARY \xff\xfe not readable as invoice""",
    "INV-Umbrella-2026-09-27.txt": """UMBRELLA CO
Invoice U-77
Total: $7,700.00
Due: 05/06/2026
Note: date format ambiguous DD/MM.
""",
}

if __name__ == "__main__":
    os.makedirs(INBOX, exist_ok=True)
    for name, content in INVOICES.items():
        p = os.path.join(INBOX, name)
        with open(p, "w", errors="replace") as f:
            f.write(content)
        print("wrote", p)
    # init ERP db
    import sqlite3
    db = os.path.join(os.path.dirname(__file__), "erp.db")
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE IF NOT EXISTS invoices(
      id INTEGER PRIMARY KEY AUTOINCREMENT, vendor TEXT, amount REAL,
      due_date TEXT, source_file TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    con.commit()
    con.close()
    print("erp db ready:", db)
