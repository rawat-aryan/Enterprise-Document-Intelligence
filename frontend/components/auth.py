"""Authentication components for Streamlit frontend."""

import os

import httpx
import streamlit as st

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")


def get_auth_headers() -> dict:
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated") and st.session_state.get("access_token"))


def require_auth():
    if not is_authenticated():
        st.error("Please login to access this page.")
        st.stop()


def api_get(endpoint: str, params: dict = None) -> dict | list | None:
    """Make authenticated GET request to API."""
    try:
        response = httpx.get(
            f"{API_BASE}{endpoint}",
            headers=get_auth_headers(),
            params=params or {},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.session_state.authenticated = False
            st.error("Session expired. Please login again.")
            st.rerun()
        else:
            st.error(f"API error {response.status_code}: {response.text[:200]}")
            return None
    except httpx.ConnectError:
        return _mock_data(endpoint)
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_post(endpoint: str, json: dict = None, files: dict = None) -> dict | None:
    """Make authenticated POST request to API."""
    try:
        kwargs = {"headers": get_auth_headers(), "timeout": 60}
        if files:
            kwargs["files"] = files
        else:
            kwargs["json"] = json or {}
        response = httpx.post(f"{API_BASE}{endpoint}", **kwargs)
        if response.status_code in (200, 201, 202):
            return response.json()
        else:
            st.error(f"API error {response.status_code}: {response.text[:200]}")
            return None
    except httpx.ConnectError:
        return {"message": "API not available - demo mode"}
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def _mock_data(endpoint: str):
    """Return mock data when API is unavailable."""
    if "/invoices" in endpoint and "stats" in endpoint:
        return {
            "total_invoices": 156,
            "total_amount": 4850000.0,
            "average_amount": 31089.74,
            "duplicate_count": 8,
            "validation_breakdown": {"valid": 132, "invalid": 14, "needs_review": 10, "pending": 0},
            "currency_breakdown": {"INR": 4850000.0},
            "monthly_totals": [
                {"month": "2024-01", "total": 420000},
                {"month": "2024-02", "total": 380000},
                {"month": "2024-03", "total": 510000},
                {"month": "2024-04", "total": 445000},
                {"month": "2024-05", "total": 620000},
                {"month": "2024-06", "total": 475000},
            ],
        }
    if "/invoices" in endpoint:
        return {
            "items": [
                {
                    "id": f"inv-{i}",
                    "document_id": f"doc-{i}",
                    "vendor_name": f"Vendor {i}",
                    "invoice_number": f"INV-2024-{1000+i}",
                    "invoice_date": "2024-06-15",
                    "total_amount": 50000 + i * 1000,
                    "currency": "INR",
                    "validation_status": "valid",
                    "is_duplicate": i % 20 == 0,
                    "confidence_score": 0.95,
                    "created_at": "2024-06-15T10:00:00",
                }
                for i in range(1, 21)
            ],
            "total": 156,
            "page": 1,
            "page_size": 20,
        }
    if "/documents" in endpoint:
        return {
            "items": [
                {
                    "id": f"doc-{i}",
                    "filename": f"invoice_{i}.pdf",
                    "doc_type": "invoice",
                    "status": "validated",
                    "confidence_score": 0.92,
                    "created_at": "2024-06-15T10:00:00",
                }
                for i in range(1, 11)
            ],
            "total": 45,
            "page": 1,
            "page_size": 20,
        }
    return {}
