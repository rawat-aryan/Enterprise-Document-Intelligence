from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Reports", layout="wide")

if not st.session_state.get("authenticated"):
    st.error("Please login first")
    st.stop()

st.title("📋 Report Generation")

import httpx

headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.subheader("Invoice Excel Report")
st.markdown("""
This report includes 5 sheets:
- **Sheet 1**: Invoice Summary (all invoices with amounts, status)
- **Sheet 2**: Vendor Analytics (spend per vendor, invoice counts)
- **Sheet 3**: Duplicate Detection (flagged duplicates with risk scores)
- **Sheet 4**: Tax Analysis (GST/tax breakdown)
- **Sheet 5**: Exceptions (OCR failures, missing data, low confidence)
""")

if st.button("Generate Excel Report", type="primary"):
    with st.spinner("Generating report..."):
        try:
            resp = httpx.get(f"{st.session_state.api_base}/reports/excel", headers=headers, timeout=60)
            if resp.status_code == 200:
                st.download_button(
                    label="Download Invoice Report (Excel)",
                    data=resp.content,
                    file_name="enterprise_invoice_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.success("Report ready for download!")
            else:
                st.error(f"Report generation failed: {resp.text}")
        except Exception as e:
            st.error(f"Error: {e}")
