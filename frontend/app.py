from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Enterprise Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "api_base" not in st.session_state:
    st.session_state.api_base = "http://localhost:8000/api/v1"


def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 Enterprise Document Intelligence")
        st.subheader("Sign In")

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="admin@company.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                try:
                    import httpx

                    resp = httpx.post(
                        f"{st.session_state.api_base}/auth/login",
                        json={"email": email, "password": password},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.authenticated = True

                        user_resp = httpx.get(
                            f"{st.session_state.api_base}/auth/me",
                            headers={"Authorization": f"Bearer {data['access_token']}"},
                        )
                        if user_resp.status_code == 200:
                            st.session_state.user = user_resp.json()
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
                except Exception as e:
                    st.error(f"Cannot connect to API: {e}")

        st.info("Demo: Use any registered account, or register via the API at /docs")


if not st.session_state.authenticated:
    login_page()
else:
    with st.sidebar:
        user = st.session_state.user or {}
        st.markdown(f"### 👤 {user.get('full_name', 'User')}")
        st.caption(f"Role: {user.get('role', 'analyst').title()}")
        st.divider()
        st.page_link("pages/01_dashboard.py", label="📊 Dashboard", icon="📊")
        st.page_link("pages/02_document_upload.py", label="📤 Upload Documents", icon="📤")
        st.page_link("pages/03_invoice_processing.py", label="🧾 Invoice Processing", icon="🧾")
        st.page_link("pages/04_analytics.py", label="📈 Analytics", icon="📈")
        st.page_link("pages/05_rag_search.py", label="🔍 Document Search", icon="🔍")
        st.page_link("pages/06_recommendations.py", label="💡 Recommendations", icon="💡")
        st.page_link("pages/07_reports.py", label="📋 Reports", icon="📋")
        st.divider()
        if st.button("Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()

    st.title("📄 Enterprise Document Intelligence")
    st.write("Welcome! Use the sidebar to navigate.")

    col1, col2, col3, col4 = st.columns(4)
    try:
        import httpx

        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        stats = httpx.get(f"{st.session_state.api_base}/invoices/stats", headers=headers, timeout=5)
        if stats.status_code == 200:
            d = stats.json()
            col1.metric("Total Invoices", d.get("total_invoices", 0))
            col2.metric("Total Amount", f"₹{d.get('total_amount', 0):,.0f}")
            col3.metric("Duplicates", d.get("duplicate_count", 0))
            col4.metric("Avg Invoice", f"₹{d.get('average_amount', 0):,.0f}")
    except Exception:
        col1.metric("Total Invoices", "--")
        col2.metric("Total Amount", "--")
        col3.metric("Duplicates", "--")
        col4.metric("Avg Invoice", "--")
