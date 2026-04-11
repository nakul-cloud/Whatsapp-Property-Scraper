from __future__ import annotations

import io

import altair as alt
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


def apply_na_for_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric_cols = {"rent_or_sell_price", "deposit"}
    for col in out.columns:
        if col in numeric_cols:
            # Convert None/NaN in numeric cols to "N/A" for display
            out[col] = out[col].fillna("N/A").astype(str).replace("nan", "N/A").replace("<NA>", "N/A")
            continue
        out[col] = out[col].astype("string").fillna("N/A")
        out[col] = out[col].replace({"": "N/A", "nan": "N/A", "<NA>": "N/A"})
    return out


def merge_combined_rows(existing: list[dict], incoming: list[dict]) -> list[dict]:
    merged = list(existing)
    seen = {
        (
            str(r.get("property_id", "")),
            str(r.get("owner_contact", "")),
            str(r.get("date_stamp", "")),
        )
        for r in merged
    }
    for r in incoming:
        key = (
            str(r.get("property_id", "")),
            str(r.get("owner_contact", "")),
            str(r.get("date_stamp", "")),
        )
        if key in seen:
            continue
        merged.append(r)
        seen.add(key)
    return merged


def render_header() -> None:
    st.markdown(
        """
        <style>
        /* Layout polish */
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2.0rem;
        }
        header[data-testid="stHeader"] {
            background: transparent;
        }
        div[data-testid="stToolbar"] {
            visibility: hidden;
            height: 0px;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(49, 51, 63, 0.12);
        }
        section[data-testid="stSidebar"] > div {
            padding-top: 1.0rem;
        }

        .app-card {
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 14px;
            padding: 14px 16px;
            background: rgba(120, 120, 120, 0.05);
            margin-bottom: 10px;
        }
        .app-card.accent {
            border-left: 6px solid var(--primary-color);
        }
        .kpi-title {
            font-size: 0.80rem;
            opacity: 0.75;
            margin-bottom: 2px;
        }
        .kpi-value {
            font-size: 1.3rem;
            font-weight: 700;
            line-height: 1.2;
        }

        /* Chart container */
        .chart-card {
            border: 1px solid rgba(49, 51, 63, 0.12);
            border-radius: 14px;
            padding: 10px 12px;
            background: rgba(255, 255, 255, 0.02);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(title: str, value: str, *, accent: bool = True) -> None:
    klass = "app-card accent" if accent else "app-card"
    st.markdown(
        f"""
        <div class="{klass}">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _parse_whatsapp_datestamp_series(s: pd.Series) -> pd.Series:
    """Best-effort parsing for values like '09/04, 2:49 pm'. Returns datetime64[ns] with NaT on failures."""
    if s is None or s.empty:
        return pd.to_datetime(pd.Series([], dtype="string"), errors="coerce")
    raw = s.astype("string").fillna("")
    # Common canonical format used by this app.
    dt = pd.to_datetime(raw, format="%d/%m, %I:%M %p", errors="coerce")
    if dt.notna().mean() >= 0.6:
        return dt
    # Try common date-only formats seen in copied lead blocks.
    for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y", "%d-%m-%y"]:
        dt2 = pd.to_datetime(raw, format=fmt, errors="coerce")
        if dt2.notna().mean() >= 0.6:
            return dt2
    # Fallback: let pandas infer.
    return pd.to_datetime(raw, errors="coerce", dayfirst=True)


def _chart_container(title: str) -> None:
    st.markdown(f"**{title}**")
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)


def _chart_container_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_analysis(df: pd.DataFrame, df_display: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data available for analysis.")
        return

    critical_cols = ["owner_contact", "area", "address", "rent_or_sell_price", "deposit"]
    filled = 0
    total = 0
    for c in critical_cols:
        if c not in df_display.columns:
            continue
        col = df_display[c].astype(str).str.strip()
        filled += (~col.isin(["N/A", "", "nan", "<NA>"])).sum()
        total += len(col)
    quality = (filled / total * 100) if total else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Leads", str(len(df)))
    with c2:
        unique_contacts = (
            df_display["owner_contact"].astype(str).replace("N/A", pd.NA).dropna().nunique()
            if "owner_contact" in df_display
            else 0
        )
        kpi_card("Unique Contacts", str(unique_contacts))
    with c3:
        avg_price = int(pd.to_numeric(df["rent_or_sell_price"], errors="coerce").dropna().mean()) if "rent_or_sell_price" in df else 0
        kpi_card("Avg Price/Rent", f"{avg_price:,}" if avg_price else "N/A")
    with c4:
        kpi_card("Data Quality", f"{quality:.1f}%")

    st.divider()

    # --- Dashboard-like charts (colorful) ---
    data_cols = set(df_display.columns)

    # 1) Data extraction timeline (if timestamp-like stamps exist)
    dt = _parse_whatsapp_datestamp_series(df_display["date_stamp"]) if "date_stamp" in data_cols else pd.Series([], dtype="datetime64[ns]")
    timeline_df = pd.DataFrame({"dt": dt}) if len(dt) else pd.DataFrame({"dt": []})
    timeline_df = timeline_df.dropna()

    # Provide a secondary series to mimic a multi-line dashboard (e.g., missing-fields count)
    missing_fields_count = None
    if "owner_contact" in data_cols:
        missing_fields_count = df_display["owner_contact"].astype(str).str.strip().isin(["N/A", "", "nan", "<NA>"]).astype(int)
    else:
        missing_fields_count = pd.Series([0] * len(df_display), dtype="int")

    if not timeline_df.empty and timeline_df["dt"].notna().any():
        timeline_df["missing_contact"] = missing_fields_count.iloc[timeline_df.index].values
        # bucket to day if time is missing, else minute
        timeline_df["bucket"] = timeline_df["dt"].dt.floor("D")
        agg = (
            timeline_df.groupby("bucket", as_index=False)
            .agg(leads=("bucket", "size"), missing_contact=("missing_contact", "sum"))
            .sort_values("bucket")
        )
        
        # If all on same day, use bar chart for date instead
        if len(agg) == 1:
            _chart_container("Data Extraction Summary")
            summary_data = pd.DataFrame({
                "metric": ["Total Leads", "Missing Contact"],
                "count": [len(timeline_df), timeline_df["missing_contact"].sum()]
            })
            chart = (
                alt.Chart(summary_data)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                .encode(
                    x=alt.X("metric:N", title=""),
                    y=alt.Y("count:Q", title="Count"),
                    color=alt.Color("metric:N", scale=alt.Scale(scheme="tableau10"), legend=None),
                    tooltip=["metric:N", "count:Q"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)
            _chart_container_end()
        else:
            long = agg.melt(id_vars=["bucket"], value_vars=["leads", "missing_contact"], var_name="series", value_name="value")
            series_labels = {"leads": "Leads", "missing_contact": "Missing Contact"}
            long["series"] = long["series"].map(series_labels).fillna(long["series"])

            _chart_container("Data Extraction")
            chart = (
                alt.Chart(long)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                .encode(
                    x=alt.X("bucket:T", title="Date"),
                    y=alt.Y("value:Q", title="Count"),
                    color=alt.Color("series:N", scale=alt.Scale(scheme="category10"), legend=alt.Legend(title="")),
                    tooltip=[
                        alt.Tooltip("bucket:T", title="Date"),
                        alt.Tooltip("series:N", title="Series"),
                        alt.Tooltip("value:Q", title="Value"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
            _chart_container_end()
    else:
        st.info("No valid timestamps found in `date_stamp` column.")

    # 2) Bottom row charts
    left, right = st.columns(2)

    with left:
        _chart_container("Property Type Distribution")
        if "property_type" in data_cols:
            vc = df_display["property_type"].astype("string").fillna("N/A")
            vc = vc.replace({"": "N/A"})
            type_counts = vc.value_counts().reset_index()
            type_counts.columns = ["property_type", "count"]
            type_counts = type_counts[type_counts["property_type"] != "N/A"]
            if type_counts.empty:
                st.info("No property type data available.")
            else:
                chart = (
                    alt.Chart(type_counts)
                    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                    .encode(
                        x=alt.X("count:Q", title="Count"),
                        y=alt.Y("property_type:N", sort="-x", title=""),
                        color=alt.Color("property_type:N", scale=alt.Scale(scheme="tableau10"), legend=None),
                        tooltip=["property_type:N", "count:Q"],
                    )
                    .properties(height=260)
                )
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No property type column found.")
        _chart_container_end()

    with right:
        _chart_container("Top Areas")
        if "area" in data_cols:
            vc = df_display["area"].astype("string").replace("N/A", pd.NA).dropna().str.strip()
            area_counts = vc.value_counts().head(12).reset_index()
            area_counts.columns = ["area", "count"]
            if area_counts.empty:
                st.info("No area data available.")
            else:
                chart = (
                    alt.Chart(area_counts)
                    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                    .encode(
                        x=alt.X("area:N", sort="-y", title=""),
                        y=alt.Y("count:Q", title="Count"),
                        color=alt.Color("area:N", scale=alt.Scale(scheme="set3"), legend=None),
                        tooltip=["area:N", "count:Q"],
                    )
                    .properties(height=260)
                )
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No area column found.")
        _chart_container_end()

    # 3) Price distribution (histogram)
    price_series = pd.to_numeric(df.get("rent_or_sell_price"), errors="coerce") if "rent_or_sell_price" in df else pd.Series([], dtype="float")
    price_series = price_series.dropna()
    st.markdown("\n")
    _chart_container("Price Distribution")
    if not price_series.empty:
        price_df = pd.DataFrame({"price": price_series})
        chart = (
            alt.Chart(price_df)
            .mark_bar(binSpacing=2, cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("price:Q", bin=alt.Bin(maxbins=20), title="Price / Rent"),
                y=alt.Y("count():Q", title="Count"),
                color=alt.Color("count():Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=[alt.Tooltip("count():Q", title="Count")],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No price data available.")
    _chart_container_end()


def main() -> None:
    load_dotenv()

    st.set_page_config(page_title="WhatsApp Property Lead Extractor", layout="wide")
    render_header()
    st.title("WhatsApp Property Lead Extractor")

    if "combined_rows" not in st.session_state:
        st.session_state.combined_rows = []
    if "latest_rows" not in st.session_state:
        st.session_state.latest_rows = []
    if "latest_meta" not in st.session_state:
        st.session_state.latest_meta = {}

    with st.sidebar:
        st.subheader("Settings")
        enable_ai = st.toggle("Enable AI Fallback (Groq)", value=False)
        
        # Groq settings (only visible when AI is enabled)
        groq_key = ""
        groq_model = env("GROQ_MODEL", "llama-3.1-70b-versatile")
        if enable_ai:
            with st.expander("🔑 Groq Configuration", expanded=True):
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
        "Paste WhatsApp chat text here (10–100 messages supported)",
        height=320,
        placeholder="[09/04, 2:49 pm] Easy Prop New:\nProperty Code: ...\nOwner: ...\nRent: 20 K\nDeposit: 60 K\n...\n\n[09/04, 3:10 pm] ...",
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        run = st.button("Process Messages", type="primary", width="stretch")
    with col2:
        st.caption("Rule-based parsing runs first. AI is only used when >3 important fields are missing, and it batches messages into one request.")

    if run:
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
        st.session_state.latest_rows = rows
        st.session_state.latest_meta = meta
        st.session_state.combined_rows = merge_combined_rows(st.session_state.combined_rows, rows)

    if not st.session_state.latest_rows:
        st.info("Process messages to see extracted leads.")
        return

    rows = st.session_state.latest_rows
    meta = st.session_state.latest_meta
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    df = normalize_df_types(df)
    df_display = apply_na_for_text_columns(df)

    combined_df = pd.DataFrame(st.session_state.combined_rows, columns=OUTPUT_COLUMNS)
    combined_df = normalize_df_types(combined_df) if not combined_df.empty else combined_df
    combined_df_display = apply_na_for_text_columns(combined_df) if not combined_df.empty else combined_df

    dl1, dl2, dl3 = st.columns([1, 1, 1])
    with dl1:
        st.download_button(
            "Download Separate CSV (Current Batch)",
            data=df_to_csv_bytes(df_display),
            file_name="whatsapp_property_leads_current.csv",
            mime="text/csv",
            width="stretch",
        )
    with dl2:
        st.download_button(
            "Download Combined CSV (All Batches)",
            data=df_to_csv_bytes(combined_df_display if not combined_df.empty else df_display),
            file_name="whatsapp_property_leads_combined.csv",
            mime="text/csv",
            width="stretch",
        )
    with dl3:
        if st.button("Reset Combined Cache", width="stretch"):
            st.session_state.combined_rows = []
            st.success("Combined cache reset.")

    tab1, tab2, tab3, tab4 = st.tabs(["Extracted Leads", "Analysis", "Failed Messages", "Processing Details"])

    with tab1:
        st.subheader("Extracted Leads")
        st.dataframe(df_display, width="stretch", hide_index=True)
        if not combined_df_display.empty:
            st.caption(f"Combined cache currently has {len(combined_df_display)} unique leads.")

    with tab2:
        st.subheader("Processing Analysis")
        render_analysis(df, df_display)

    with tab3:
        failed = meta.get("audit_failed", []) or []
        if not failed:
            st.success("No failed messages. All important fields were extracted.")
        else:
            fail_df = pd.DataFrame(failed, columns=["idx", "date_stamp", "missing_fields", "raw_message"])
            if "missing_fields" in fail_df.columns:
                fail_df["missing_fields"] = fail_df["missing_fields"].fillna("NA").replace({"": "NA"})
            fail_df = apply_na_for_text_columns(fail_df)
            st.dataframe(fail_df, width="stretch", hide_index=True)
            st.download_button(
                "Download failed-messages CSV",
                data=df_to_csv_bytes(fail_df),
                file_name="failed_messages_audit.csv",
                mime="text/csv",
                width="stretch",
            )

    with tab4:
        st.json({k: v for k, v in meta.items() if k != "debug"})
        if meta.get("failures"):
            st.warning("Some failures occurred. See details above.")


if __name__ == "__main__":
    main()

