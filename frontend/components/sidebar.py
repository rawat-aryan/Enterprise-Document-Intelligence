"""Sidebar navigation component."""
import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/document.png", width=48)
        st.title("DocIntel")
        st.divider()

        user = st.session_state.get("user") or {}
        if user:
            st.markdown(f"**{user.get('full_name', 'User')}**")
            st.caption(f"Role: {user.get('role', 'analyst').capitalize()}")
            if user.get("tenant_id"):
                st.caption(f"Tenant: {user['tenant_id'][:8]}...")
        st.divider()

        nav_items = [
            ("📊 Dashboard", "pages/01_dashboard.py"),
            ("📤 Upload Documents", "pages/02_document_upload.py"),
            ("🧾 Invoice Processing", "pages/03_invoice_processing.py"),
            ("📈 Analytics", "pages/04_analytics.py"),
            ("🔍 Document Search", "pages/05_rag_search.py"),
            ("💡 Recommendations", "pages/06_recommendations.py"),
            ("📋 Reports", "pages/07_reports.py"),
        ]
        for label, page in nav_items:
            st.page_link(page, label=label)

        st.divider()
        if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()
