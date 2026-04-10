from __future__ import annotations

import io

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from parser import OUTPUT_COLUMNS, process_raw_text
from utils import env, normalize_whitespace


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def normalize_df_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Keep nullable integers to avoid Arrow errors from mixed '' + int types.
    for col in ["rent_or_sell_price", "deposit"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    return out


def main() -> None:
    load_dotenv()

    st.set_page_config(page_title="WhatsApp Property Lead Extractor", layout="wide")
    st.title("WhatsApp Property Lead Extractor")

    with st.sidebar:
        st.subheader("Settings")
        enable_ai = st.toggle("Enable AI Fallback (Groq)", value=False)
        groq_key = st.text_input("Groq API key (GROQ_API_KEY)", type="password", value=env("GROQ_API_KEY"))

        model_options = [
            env("GROQ_MODEL", "llama-3.1-70b-versatile"),
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "deepseek-r1-distill-llama-70b",
            "mixtral-8x7b-32768",
            "Custom…",
        ]
        # de-dupe while preserving order
        seen = set()
        model_options = [m for m in model_options if not (m in seen or seen.add(m))]
        selected_model = st.selectbox("Groq model", options=model_options, index=0)
        groq_model = selected_model
        if selected_model == "Custom…":
            groq_model = st.text_input("Custom Groq model id", value=env("GROQ_MODEL", "llama-3.1-70b-versatile"))

        area_path = st.text_input(
            "Custom Pune areas file path (optional)",
            value=env("AREAS_FILE", ""),
            help="Leave blank to use bundled ./areas_pune.txt",
        )

    raw = st.text_area(
        "Paste WhatsApp chat text here (10–50 messages supported)",
        height=320,
        placeholder="[09/04, 2:49 pm] Easy Prop New:\nProperty Code: ...\nOwner: ...\nRent: 20 K\nDeposit: 60 K\n...\n\n[09/04, 3:10 pm] ...",
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        run = st.button("Process Messages", type="primary", width="stretch")
    with col2:
        st.caption("Rule-based parsing runs first. AI is only used when >3 important fields are missing, and it batches messages into one request.")

    if not run:
        return

    raw = normalize_whitespace(raw)
    if not raw:
        st.warning("Please paste WhatsApp messages first.")
        return

    with st.spinner("Processing messages..."):
        rows, meta = process_raw_text(
            raw,
            enable_ai_fallback=enable_ai,
            groq_api_key=groq_key,
            groq_model=groq_model,
            area_paths=[area_path] if area_path.strip() else None,
        )

    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    df = normalize_df_types(df)

    st.subheader("Extracted Leads")
    st.dataframe(df, width="stretch", hide_index=True)

    st.download_button(
        "Download CSV",
        data=df_to_csv_bytes(df),
        file_name="whatsapp_property_leads.csv",
        mime="text/csv",
        width="stretch",
    )

    with st.expander("Audit / Failed messages (raw + missing fields)"):
        failed = meta.get("audit_failed", []) or []
        if not failed:
            st.success("No failed messages. All important fields were extracted.")
        else:
            fail_df = pd.DataFrame(failed, columns=["idx", "date_stamp", "missing_fields", "raw_message"])
            st.dataframe(fail_df, width="stretch", hide_index=True)
            st.download_button(
                "Download failed-messages CSV",
                data=df_to_csv_bytes(fail_df),
                file_name="failed_messages_audit.csv",
                mime="text/csv",
                width="stretch",
            )

    with st.expander("Processing details"):
        st.json({k: v for k, v in meta.items() if k != "debug"})
        if meta.get("failures"):
            st.warning("Some failures occurred. See details above.")


if __name__ == "__main__":
    main()

