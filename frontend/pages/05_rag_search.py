from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Document Search", layout="wide")

if not st.session_state.get("authenticated"):
    st.error("Please login first")
    st.stop()

st.title("🔍 Document Search (RAG)")
st.markdown("Search across all documents using natural language.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

query = st.chat_input("Ask about your documents...")

if query:
    st.session_state.chat_history.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):
            try:
                import asyncio

                from backend.app.services.rag_service import rag_service

                result = asyncio.run(rag_service.query(query))
                answer = result.get("answer", "No answer found.")
                sources = result.get("sources", [])

                st.write(answer)
                if sources:
                    with st.expander("Sources"):
                        for s in sources:
                            st.caption(f"- {s}")

                st.session_state.chat_history.append({"role": "assistant", "content": answer})
            except Exception as e:
                msg = f"Search service unavailable: {e}"
                st.error(msg)
                st.session_state.chat_history.append({"role": "assistant", "content": msg})
