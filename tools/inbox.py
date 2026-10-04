"""Inbox + invoice parsing tools over local mock_env/inbox/."""
import os
import re
import glob
from tools.base import Tool, Observation

INBOX_DIR = os.getenv("INBOX_DIR", "mock_env/inbox")


def _read_text(path: str) -> str:
    # try plain text first
    try:
        with open(path, "r", errors="replace") as f:
            txt = f.read()
        if len(txt.strip()) > 10:
            return txt
    except Exception:
        pass
    # try pdf
    if path.lower().endswith(".pdf"):
        for loader in ("pdfplumber", "pypdf"):
            try:
                if loader == "pdfplumber":
                    import pdfplumber
                    with pdfplumber.open(path) as pdf:
                        return "\n".join([(p.extract_text() or "") for p in pdf.pages])
                else:
                    from pypdf import PdfReader
                    r = PdfReader(path)
                    return "\n".join([(p.extract_text() or "") for p in r.pages])
            except Exception:
                continue
    return ""


def parse_amount_date(text: str):
    amt = None
    # prefer "Total: 12,340.00" / "Amount Due $123.45"
    patterns = [
        r"(?:total|amount due|balance due|grand total)[^\d$₹]{0,10}[$₹]?\s*([\d,]+\.\d{2})",
        r"[$₹]\s*([\d,]+\.\d{2})",
        r"([\d,]+\.\d{2})",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                amt = float(m.group(1).replace(",", ""))
                break
            except ValueError:
                continue
    # dates: prefer explicit Due: YYYY-MM-DD, then any YYYY-MM-DD not in invoice-id line, then DD/MM/YYYY
    due = None
    m = re.search(r"due[^\d]{0,15}(\d{4}-\d{2}-\d{2})", text, re.I)
    if m:
        due = m.group(1)
    else:
        # collect all ISO dates, prefer one on a line containing 'due'
        all_iso = re.findall(r"(\d{4}-\d{2}-\d{2})", text)
        due_line = [d for line in text.splitlines() for d in re.findall(r"(\d{4}-\d{2}-\d{2})", line) if "due" in line.lower()]
        if due_line:
            due = due_line[0]
        elif all_iso:
            # skip invoice-id date if multiple present: prefer last (Due line is usually last)
            due = all_iso[-1]
    if not due:
        m = re.search(r"due[^\d]{0,15}(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text, re.I)
        if m:
            # assume DD/MM/YYYY unless first > 12 -> MM/DD fallback handled as DD/MM
            dd, mm, yyyy = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
            due = f"{yyyy}-{mm}-{dd}"
        else:
            m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
            if m:
                dd, mm, yyyy = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
                due = f"{yyyy}-{mm}-{dd}"
    return amt, due


class InboxSearchTool(Tool):
    name = "inbox.search"
    description = "Search mock inbox for vendor invoices. Args: vendor (substring), sort=latest. Returns candidates sorted newest first."
    schema = {"type": "object", "properties": {
        "vendor": {"type": "string"}, "sort": {"type": "string"}}}

    def execute(self, args):
        vendor = (args.get("vendor") or "").lower().strip()
        files = sorted(glob.glob(os.path.join(INBOX_DIR, "*")))
        cands = []
        for fp in files:
            base = os.path.basename(fp).lower()
            txt_head = ""
            if fp.endswith(".txt"):
                try:
                    with open(fp, errors="replace") as f:
                        txt_head = f.read(2000).lower()
                except Exception:
                    pass
            # match vendor substring against filename or content; empty vendor = all
            if not vendor or vendor in base or vendor in txt_head or "acme" in base and "acme" in vendor:
                # date from filename or mtime
                m = re.search(r"(\d{4}-\d{2}-\d{2})", base)
                date = m.group(1) if m else ""
                cands.append({"path": fp, "vendor": os.path.basename(fp),
                              "date": date, "mtime": os.path.getmtime(fp)})
        # vendor fallback: if filter too strict and nothing found, return all
        if not cands and vendor:
            for fp in files:
                cands.append({"path": fp, "vendor": os.path.basename(fp), "date": "", "mtime": os.path.getmtime(fp)})
            return Observation(ok=True, data={"candidates": sorted(cands, key=lambda c: c["mtime"], reverse=True),
                                              "note": f"no exact match for '{vendor}', showing all"})
        cands = sorted(cands, key=lambda c: (c.get("date") or "", c["mtime"]), reverse=True)
        if not cands:
            return Observation(ok=False, error="inbox empty, nothing to process")
        return Observation(ok=True, data={"candidates": cands, "vendor": vendor or "(any)"})


class InvoiceParseTool(Tool):
    name = "invoice.parse"
    description = "Extract vendor, amount, due_date from an invoice file. Args: path (optional; defaults to latest). Never invent numbers."
    schema = {"type": "object", "properties": {"path": {"type": "string"}}}

    def execute(self, args):
        path = args.get("path") or ""
        if not path:
            import re as _re
            def _fdate(p):
                m = _re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(p))
                return m.group(1) if m else ""
            files = sorted(glob.glob(os.path.join(INBOX_DIR, "*")),
                           key=lambda p: (_fdate(p), os.path.getmtime(p)), reverse=True)
            # skip known-corrupt file first pass
            for fp in files:
                if "corrupt" not in fp.lower():
                    path = fp
                    break
            else:
                path = files[0] if files else ""
        if not path or not os.path.exists(path):
            return Observation(ok=False, error=f"invoice file not found: {path}")
        if "corrupt" in os.path.basename(path).lower():
            return Observation(ok=False, error=f"{path} is corrupt/unreadable, try another candidate",
                               evidence={"tried": path})
        text = _read_text(path)
        if len(text.strip()) < 10:
            return Observation(ok=False, error=f"{path} unreadable by text+pdf parsers, try another file")
        amt, due = parse_amount_date(text)
        # vendor guess from content or filename
        m = re.search(r"(Acme Corp|Globex|Initech|Umbrella)", text, re.I)
        vendor = m.group(1) if m else os.path.basename(path).split("-")[1] if "-" in os.path.basename(path) else "Unknown"
        if amt is None or due is None:
            return Observation(ok=False,
                               error=f"could not extract amount/due_date from {path} (amount={amt}, due={due})",
                               evidence={"tried": path, "snippet": text[:400]})
        inv_id = os.path.splitext(os.path.basename(path))[0]
        return Observation(ok=True,
                           data={"vendor": vendor, "amount": amt, "due_date": due,
                                 "invoice_id": inv_id, "invoice_path": path},
                           evidence={"source_file": path})
