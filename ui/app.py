"""Streamlit UI: live trace viewer + approvals. Run: streamlit run ui/app.py"""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st

st.set_page_config(page_title="Autonomous AI Task Worker", layout="wide")
st.title("Autonomous AI Task Worker — prototype")

task = st.text_input("Natural-language task",
    "Find the latest invoice from Acme Corp, extract amount and due date, enter into internal system.")
auto = st.checkbox("Auto-approve ERP writes (skip confirmation)", value=True)
if st.button("Run task"):
    from agent.loop import run
    with st.spinner("Worker running... see terminal for approval prompts (if not auto)."):
        result = run(task, auto_approve=auto, verbose=False)
    st.session_state["last"] = result
    st.rerun()

res = st.session_state.get("last")
if res:
    v = res["verification"]
    st.success(f"Verified: {v['verified']} — {v['detail']}" if v["verified"] else f"NOT verified — {v['detail']}")
    st.subheader("Summary")
    st.write(res.get("summary") or "(see facts)")
    st.subheader("Facts (memory)")
    st.json(res["facts"])
    st.subheader("Thought → Action → Observation trace")
    for h in res["history"]:
        with st.expander(f"Step {h['step']}: {h['thought'][:90]} → {h['action']}"):
            st.write("**Thought:**", h["thought"])
            st.write("**Action:**", h["action"], h["args"])
            st.write("**Observation:**", h["observation"])
    logs = sorted(glob.glob("trajectory_logs/*.json"))[-5:]
    st.caption("Recent trajectory logs: " + ", ".join(logs))

st.divider()
st.caption("Mock ERP: run `uvicorn mock_env.erp_server:app --port 8000` · UI at /ui · DB mock_env/erp.db")
