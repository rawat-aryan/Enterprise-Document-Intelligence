from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Analytics", layout="wide")

if not st.session_state.get("authenticated"):
    st.error("Please login first")
    st.stop()

st.title("📈 Natural Language Analytics")
st.markdown("Ask questions in plain English and get instant SQL + visualizations.")

example_queries = [
    "Which vendor has the highest total spend?",
    "Show me all invoices above 50000 rupees",
    "How many duplicate invoices are there per vendor?",
    "What is the monthly invoice trend?",
    "Show contracts expiring in the next 60 days",
    "Which vendors have the most invoices?",
]

selected = st.selectbox("Try an example", [""] + example_queries)
question = st.text_input("Or type your question", value=selected or "")

if st.button("Run Query", type="primary") and question:
    import httpx
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    with st.spinner("Generating SQL and running query..."):
        try:
            resp = httpx.post(
                f"{st.session_state.api_base}/analytics/query",
                json={"question": question},
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json()

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown("**Generated SQL**")
                    st.code(result["sql"], language="sql")
                    st.caption(f"Execution time: {result['execution_time_ms']}ms")

                with col2:
                    if result.get("insights"):
                        st.markdown("**AI Insights**")
                        st.info(result["insights"])

                if result.get("results"):
                    df = pd.DataFrame(result["results"])
                    st.markdown(f"**Results** ({len(df)} rows)")
                    st.dataframe(df, use_container_width=True)

                    # Auto chart if numeric columns exist
                    numeric_cols = df.select_dtypes(include="number").columns.tolist()
                    string_cols = df.select_dtypes(include="object").columns.tolist()
                    if numeric_cols and string_cols:
                        fig = px.bar(df.head(20), x=string_cols[0], y=numeric_cols[0],
                                    title=f"{string_cols[0]} vs {numeric_cols[0]}")
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Query returned no results")
            else:
                st.error(f"Query failed: {resp.text}")
        except Exception as e:
            st.error(f"Error: {e}")
