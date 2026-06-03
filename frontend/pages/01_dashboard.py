from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Dashboard", layout="wide")

if not st.session_state.get("authenticated"):
    st.error("Please login first")
    st.stop()

st.title("📊 Executive Dashboard")

headers = {"Authorization": f"Bearer {st.session_state.token}"}
api_base = st.session_state.api_base

try:
    import httpx

    stats_resp = httpx.get(f"{api_base}/invoices/stats", headers=headers, timeout=10)
    spend_resp = httpx.get(f"{api_base}/analytics/spend", headers=headers, timeout=10)

    if stats_resp.status_code == 200:
        stats = stats_resp.json()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Invoices", stats["total_invoices"])
        col2.metric("Total Spend", f"₹{stats['total_amount']:,.0f}")
        col3.metric(
            "Duplicates Found",
            stats["duplicate_count"],
            delta=f"-₹{stats['average_amount'] * stats['duplicate_count']:,.0f} risk",
        )
        col4.metric("Avg Invoice Value", f"₹{stats['average_amount']:,.0f}")

        st.divider()
        col_left, col_right = st.columns(2)

        # Monthly trend
        if stats.get("monthly_totals"):
            df_monthly = pd.DataFrame(stats["monthly_totals"])
            fig_trend = px.line(df_monthly, x="month", y="total", title="Monthly Invoice Spend", markers=True)
            fig_trend.update_layout(yaxis_tickprefix="₹", height=350)
            col_left.plotly_chart(fig_trend, use_container_width=True)

        # Validation breakdown
        if stats.get("validation_breakdown"):
            vb = stats["validation_breakdown"]
            fig_val = px.pie(
                names=list(vb.keys()),
                values=list(vb.values()),
                title="Validation Status Distribution",
                color_discrete_map={
                    "valid": "#22c55e",
                    "invalid": "#ef4444",
                    "pending": "#f59e0b",
                    "needs_review": "#3b82f6",
                },
            )
            fig_val.update_layout(height=350)
            col_right.plotly_chart(fig_val, use_container_width=True)

    if spend_resp.status_code == 200:
        spend = spend_resp.json()
        if spend.get("vendors"):
            df_vendors = pd.DataFrame(spend["vendors"])
            fig_vendors = px.bar(
                df_vendors.head(10),
                x="vendor",
                y="total_spend",
                title="Top 10 Vendors by Spend",
                color="total_spend",
                color_continuous_scale="Blues",
            )
            fig_vendors.update_layout(yaxis_tickprefix="₹", height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_vendors, use_container_width=True)

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Ensure the API server is running at " + api_base)
