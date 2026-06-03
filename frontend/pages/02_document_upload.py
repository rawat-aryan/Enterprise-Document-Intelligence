from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Upload Documents", layout="wide")

if not st.session_state.get("authenticated"):
    st.error("Please login first")
    st.stop()

st.title("📤 Document Upload")

tab1, tab2 = st.tabs(["Single Document", "Bulk Upload (ZIP)"])

with tab1:
    st.subheader("Upload a Single Document")
    doc_type = st.selectbox("Document Type", ["invoice", "contract", "report", "other"])
    uploaded_file = st.file_uploader("Choose file", type=["pdf", "png", "jpg", "jpeg", "tiff", "txt"])

    if uploaded_file and st.button("Upload & Process", type="primary"):
        import httpx
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        with st.spinner("Uploading and processing..."):
            try:
                resp = httpx.post(
                    f"{st.session_state.api_base}/documents/upload",
                    params={"doc_type": doc_type},
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                    headers=headers,
                    timeout=60,
                )
                if resp.status_code == 201:
                    doc = resp.json()
                    st.success(f"Uploaded! Document ID: {doc['id']}")
                    st.json(doc)
                else:
                    st.error(f"Upload failed: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")

with tab2:
    st.subheader("Bulk Upload (ZIP File)")
    st.info("Upload a ZIP file containing multiple invoices/documents. All supported formats will be processed.")
    zip_doc_type = st.selectbox("Document Type for all files", ["invoice", "contract", "report", "other"], key="bulk_type")
    zip_file = st.file_uploader("Choose ZIP file", type=["zip"])

    if zip_file and st.button("Upload ZIP & Process All", type="primary"):
        import httpx
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        with st.spinner(f"Uploading {zip_file.name}..."):
            try:
                resp = httpx.post(
                    f"{st.session_state.api_base}/documents/bulk-upload",
                    params={"doc_type": zip_doc_type},
                    files={"file": (zip_file.name, zip_file.getvalue(), "application/zip")},
                    headers=headers,
                    timeout=120,
                )
                if resp.status_code == 202:
                    data = resp.json()
                    st.success(f"{data['message']}")
                    st.write(f"Document IDs: {data['document_ids'][:5]}{'...' if len(data['document_ids']) > 5 else ''}")
                else:
                    st.error(f"Upload failed: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")
