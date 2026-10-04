import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_invoice_parse_latest():
    os.environ["INBOX_DIR"] = "mock_env/inbox"
    from tools.inbox import InvoiceParseTool
    # ensure seed exists
    assert os.path.exists("mock_env/inbox"), "run mock_env/seed_data.py first"
    obs = InvoiceParseTool().execute({})
    assert obs.ok, f"parse failed: {obs.error}"
    assert isinstance(obs.data["amount"], float)
    assert obs.data["due_date"].count("-") == 2
    print("test_invoice_parse_latest OK:", obs.data)

def test_erp_create_and_verify():
    from tools.erp_api import ERPCreateTool, ERPGetTool
    obs = ERPCreateTool().execute({"vendor": "TestCo", "amount": 123.45,
                                   "due_date": "2026-11-01", "invoice_id": "TEST-1"})
    assert obs.ok, obs.error
    obs2 = ERPGetTool().execute({"erp_id": obs.data["erp_id"]})
    assert obs2.ok and obs2.data["amount"] == 123.45
    print("test_erp_create_and_verify OK:", obs.data)

def test_end_to_end_invoice():
    os.environ["AUTO_APPROVE"] = "1"
    os.environ["REQUIRE_APPROVAL"] = "false"
    os.environ["MODEL_PROVIDER"] = "mock"
    from agent.loop import run
    r = run("Find the latest invoice from Acme Corp, extract amount and due date, enter into internal system.",
            auto_approve=True, verbose=False)
    assert r["verification"]["verified"], r["verification"]
    print("test_end_to_end_invoice OK:", r["verification"]["detail"])

if __name__ == "__main__":
    test_invoice_parse_latest()
    test_erp_create_and_verify()
    test_end_to_end_invoice()
    print("ALL TESTS PASSED")
