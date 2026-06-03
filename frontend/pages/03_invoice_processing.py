from __future__ import annotations

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Invoice Processing", layout="wide")

if not st.session_state.get("authenticated"):
    st.error("Please login first")
    st.stop()

st.title("🧾 Invoice Processing")

import httpx
headers = {"Authorization": f"Bearer {st.session_state.token}"}

col1, col2, col3 = st.columns(3)
vendor_filter = col1.text_input("Filter by vendor", "")
status_filter = col2.selectbox("Validation Status", ["", "valid", "invalid", "pending", "needs_review"])
show_duplicates = col3.checkbox("Show duplicates only")

params = {"page": 1, "page_size": 100}
if vendor_filter:
    params["vendor"] = vendor_filter
if status_filter:
    params["validation_status"] = status_filter
if show_duplicates:
    params["duplicates_only"] = True

try:
    resp = httpx.get(f"{st.session_state.api_base}/invoices/", params=params, headers=headers, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        st.caption(f"Showing {len(data['items'])} of {data['total']} invoices")

        if data["items"]:
            df = pd.DataFrame(data["items"])
            display_cols = ["invoice_number", "vendor_name", "invoice_date", "total_amount", "currency",
                           "tax_amount", "validation_status", "is_duplicate", "confidence_score"]
            df_display = df[[c for c in display_cols if c in df.columns]]

            # Color duplicates
            def highlight_duplicates(row):
                if row.get("is_duplicate"):
                    return ["background-color: #fee2e2"] * len(row)
                return [""] * len(row)

            st.dataframe(df_display, use_container_width=True, height=500)

            # Download Excel
            st.divider()
            if st.button("Download Excel Report", type="primary"):
                excel_resp = httpx.get(f"{st.session_state.api_base}/reports/excel", headers=headers, timeout=30)
                if excel_resp.status_code == 200:
                    st.download_button(
                        "Save Excel File",
                        data=excel_resp.content,
                        file_name="invoice_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
        else:
            st.info("No invoices found. Upload documents to get started.")
except Exception as e:
    st.error(f"Error loading invoices: {e}")
