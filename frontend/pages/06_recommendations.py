from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Recommendations", layout="wide")

if not st.session_state.get("authenticated"):
    st.error("Please login first")
    st.stop()

st.title("💡 AI Recommendations")
import httpx

headers = {"Authorization": f"Bearer {st.session_state.token}"}

tab1, tab2, tab3 = st.tabs(["Vendor Performance", "Cost Optimization", "Contract Alerts"])

with tab1:
    with st.spinner("Analyzing vendor performance..."):
        try:
            resp = httpx.get(f"{st.session_state.api_base}/recommendations/vendors", headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("insights"):
                    st.info(data["insights"])
                if data.get("vendors"):
                    df = pd.DataFrame(data["vendors"])
                    fig = px.scatter(
                        df,
                        x="total_invoices",
                        y="total_spend",
                        size="avg_amount",
                        hover_name="vendor",
                        title="Vendor Risk vs Spend",
                        color="duplicate_rate",
                        color_continuous_scale="RdYlGn_r",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    with st.spinner("Computing cost optimization opportunities..."):
        try:
            resp = httpx.get(
                f"{st.session_state.api_base}/recommendations/cost-optimization", headers=headers, timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Invoices", data.get("total_invoices", 0))
                col2.metric("Duplicate Invoices", data.get("duplicate_invoices", 0))
                col3.metric("Potential Savings", f"₹{data.get('potential_savings_from_duplicates', 0):,.0f}")
                if data.get("recommendations"):
                    st.info(data["recommendations"])
        except Exception as e:
            st.error(f"Error: {e}")

with tab3:
    with st.spinner("Checking contract alerts..."):
        try:
            resp = httpx.get(f"{st.session_state.api_base}/recommendations/contracts", headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("insights"):
                    st.warning(data["insights"])
                if data.get("expiring_contracts"):
                    df = pd.DataFrame(data["expiring_contracts"])
                    st.error(f"⚠️ {len(df)} contracts expiring within 60 days!")
                    st.dataframe(df, use_container_width=True)
                else:
                    st.success("No contracts expiring in the next 60 days.")
        except Exception as e:
            st.error(f"Error: {e}")
