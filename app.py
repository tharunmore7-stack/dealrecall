import json
import os
from datetime import date, datetime, timezone, timedelta
from dotenv import load_dotenv
import streamlit as st
from core import DEALS, bank_id, notes, prepare, save_note

load_dotenv()
st.set_page_config(page_title="DealRecall", page_icon="🧠", layout="wide")
st.title("DealRecall")
st.caption("Remember the objection. Keep the promise. Prepare the next conversation.")
st.info("Hackathon prototype • Synthetic deals • Drafts only — no messages are sent")

with st.sidebar:
    st.header("Workspace")
    deal = st.selectbox("Deal", list(DEALS), format_func=DEALS.get)
    st.caption("Each deal uses a separate Hindsight memory bank.")
    if st.button("New session / clear results"):
        st.session_state.pop("outputs", None)
        st.rerun()
    st.caption("Clearing results does not delete persistent deal memory.")
    for name in ("HINDSIGHT_BASE_URL", "HINDSIGHT_API_KEY", "LLM_API_KEY", "LLM_MODEL", "HINDSIGHT_BANK_PREFIX"):
        value = os.getenv(name, "")
        st.write(f"{'✓' if value and not value.startswith('PASTE') else '○'} {name}")


def clients():
    for name in ("HINDSIGHT_BASE_URL", "HINDSIGHT_API_KEY", "LLM_API_KEY", "LLM_MODEL"):
        if not os.getenv(name) or os.getenv(name, "").startswith("PASTE"):
            raise ValueError(f"Fill {name} in .env and restart the app")
    from hindsight_client import Hindsight
    from openai import OpenAI
    return Hindsight(base_url=os.environ["HINDSIGHT_BASE_URL"], api_key=os.environ["HINDSIGHT_API_KEY"], timeout=90), OpenAI(base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"), api_key=os.environ["LLM_API_KEY"], timeout=60, max_retries=1)


def error(exc):
    if isinstance(exc, (ValueError, RuntimeError)):
        st.error(str(exc))
    else:
        st.error(f"Service request failed ({type(exc).__name__}). Check credentials, model access, quota and connection. No simulated result has been substituted.")

left, right = st.columns([1, 1.4])
with left:
    st.subheader("1 · Record an interaction")
    with st.form(f"note-{deal}"):
        india = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(india)
        day = st.date_input("Interaction date", value=now.date())
        clock = st.time_input("Interaction time (IST)", value=now.time().replace(second=0, microsecond=0))
        kind = st.selectbox("Type", ["Meeting", "Outcome", "Correction"])
        content = st.text_area("Meeting notes or confirmed outcome", height=180, max_chars=12000,
            placeholder="Who said what? Which offer was rejected? What was promised? Was it actually completed?")
        confirmed = st.checkbox("I reviewed these notes before saving")
        submitted = st.form_submit_button("Save to Hindsight", type="primary")
    if submitted:
        if not confirmed:
            st.warning("Review and confirm the notes first.")
        else:
            try:
                mem, _ = clients()
                with mem, st.spinner("Retaining the interaction in Hindsight…"):
                    ident = save_note(mem, deal, datetime.combine(day, clock, tzinfo=india).isoformat(), kind, content)
                st.success(f"Saved note {ident}. Use Prepare to check recall.")
                st.session_state.pop("outputs", None)
            except Exception as exc:
                error(exc)
    with st.expander("Saved source notes and write status"):
        for note in notes(deal):
            st.caption(f"{note['occurred']} · {note['kind']} · {note['status']} · {note['id']}")
            st.text(note["content"])

with right:
    st.subheader("2 · Prepare the next conversation")
    request = st.text_area("What do you need?", "Prepare my next follow-up. What must I address, what should I avoid, and what is the next action?", max_chars=4000)
    compare = st.checkbox("Compare memory OFF and ON", value=False)
    if st.button("Prepare brief and draft", type="primary"):
        st.session_state.pop("outputs", None)
        try:
            mem, llm = clients()
            outputs = []
            with mem, llm, st.spinner("Recalling history and preparing the follow-up…"):
                for enabled in ([False, True] if compare else [True]):
                    outputs.append(prepare(mem, llm, deal, request, enabled))
            st.session_state.outputs = {"deal": deal, "items": outputs}
        except Exception as exc:
            error(exc)
    saved = st.session_state.get("outputs", {})
    if saved.get("deal") == deal:
        for output in saved["items"]:
            st.markdown(f"### Memory {'ON' if output['memory_enabled'] else 'OFF'}")
            result = output["result"]
            st.write(result["brief"])
            st.markdown("**Recommended next action**")
            st.write(result["next_action"])
            for title, key in [("Open commitments", "open_commitments"), ("Avoid", "avoid"), ("Questions", "questions")]:
                st.markdown(f"**{title}**")
                for item in result[key]:
                    st.write("• " + item)
            st.markdown("**Follow-up draft — review before using**")
            st.text(result["follow_up_draft"])
            with st.expander("Memory evidence and execution trace", expanded=output["memory_enabled"]):
                st.caption("Retrieved evidence; references are not a guarantee that every generated claim is correct.")
                for evidence in output["evidence"]:
                    st.write(f"{evidence['id']}: {evidence['text']}")
                st.write(output["trace"])
                st.json(output["evidence"])
        st.download_button("Download this run", json.dumps(saved, indent=2), "dealrecall-run.json", "application/json")
