import os
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = os.getenv(
    "RAG_API_URL",
    "http://localhost:8000",
).rstrip("/")

REQUEST_TIMEOUT = 60


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="RAG Pipeline",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# API HELPERS
# ============================================================

def api_get(endpoint):
    response = requests.get(
        f"{API_URL}{endpoint}",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def api_post(endpoint, payload=None):
    response = requests.post(
        f"{API_URL}{endpoint}",
        json=payload or {},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def upload_document(uploaded_file):
    response = requests.post(
        f"{API_URL}/documents",
        files={
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf",
            )
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def get_documents():
    try:
        data = api_get("/documents")

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("documents", [])

        return []

    except Exception:
        return []


def check_api():
    try:
        api_get("/health")
        return True
    except Exception:
        return False


documents = get_documents()
api_online = check_api()


# ============================================================
# NORMALIZE DOCUMENT DATA
# ============================================================

indexed_documents = len(documents)

total_pages = 0
total_chunks = 0

for document in documents:

    try:
        total_pages += int(
            document.get("page_count", 0) or 0
        )
    except (TypeError, ValueError):
        pass

    try:
        total_chunks += int(
            document.get("chunk_count", 0) or 0
        )
    except (TypeError, ValueError):
        pass


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("📚 RAG Pipeline")

    st.caption(
        "Local document intelligence workspace"
    )

    st.divider()

    if api_online:
        st.success("● API Connected")
    else:
        st.error("● API Offline")

    st.subheader("WORKSPACE")

    navigation = st.radio(
        "Navigation",
        [
            "Document Search",
            "Ask Documents",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.subheader("COLLECTION")

    st.metric(
        "Indexed Documents",
        indexed_documents,
    )

    st.metric(
        "Total Pages",
        total_pages,
    )

    st.metric(
        "Vector Chunks",
        total_chunks,
    )

    st.divider()

    st.caption(
        "Documents are chunked and indexed. "
        "Relevant chunks are retrieved before "
        "the LLM generates an answer."
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.title("Document Intelligence")

st.write(
    "Search your indexed documents and ask questions "
    "using retrieval-augmented generation."
)


# ============================================================
# TOP METRICS
# ============================================================

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        "📄 Indexed Documents",
        indexed_documents,
    )

with metric2:
    st.metric(
        "📑 Total Pages",
        total_pages,
    )

with metric3:
    st.metric(
        "🧩 Vector Chunks",
        total_chunks,
    )


# ============================================================
# DOCUMENT SEARCH PAGE
# ============================================================

if navigation == "Document Search":

    st.divider()

    st.header("Document Search")

    search_text = st.text_input(
        "Search",
        placeholder="Search documents by filename...",
    )

    if search_text.strip():

        query = search_text.lower().strip()

        filtered_documents = [
            document
            for document in documents
            if query in str(
                document.get("filename", "")
            ).lower()
        ]

    else:
        filtered_documents = documents

    st.caption(
        f"{len(filtered_documents)} document(s)"
    )

    if not filtered_documents:

        st.info(
            "No documents found. Upload a PDF to begin."
        )

    else:

        for document in filtered_documents:

            filename = document.get(
                "filename",
                "Unknown document",
            )

            status = str(
                document.get(
                    "status",
                    "unknown",
                )
            ).lower()

            pages = document.get(
                "page_count",
                "—",
            )

            chunks = document.get(
                "chunk_count",
                "—",
            )

            with st.container(border=True):

                left, center, right = st.columns(
                    [5, 2, 1]
                )

                with left:

                    st.write(
                        f"### 📄 {filename}"
                    )

                    st.caption(
                        f"{pages} pages  •  "
                        f"{chunks} chunks"
                    )

                with center:

                    if status in (
                        "done",
                        "completed",
                        "indexed",
                        "success",
                    ):

                        st.success(
                            "Indexed"
                        )

                    elif status in (
                        "processing",
                        "running",
                    ):

                        st.info(
                            "Processing"
                        )

                    elif status in (
                        "queued",
                        "pending",
                    ):

                        st.info(
                            "Queued"
                        )

                    elif status in (
                        "failed",
                        "error",
                    ):

                        st.error(
                            "Failed"
                        )

                    else:

                        st.caption(
                            status.title()
                        )

                with right:

                    st.caption("PDF")

    # ========================================================
    # UPLOAD
    # ========================================================

    st.divider()

    st.header("Add Documents")

    st.write(
        "Upload a PDF to add it to the document collection."
    )

    uploaded_file = st.file_uploader(
        "PDF document",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file:

        st.info(
            f"Selected: {uploaded_file.name}"
        )

        if st.button(
            "Upload PDF",
            type="primary",
            use_container_width=False,
        ):

            try:

                with st.spinner(
                    "Uploading and processing document..."
                ):

                    result = upload_document(
                        uploaded_file
                    )

                st.success(
                    "Document uploaded successfully."
                )

                if isinstance(result, dict):

                    message = result.get(
                        "message"
                    )

                    if message:
                        st.info(message)

                st.rerun()

            except requests.HTTPError as exc:

                st.error(
                    f"Upload failed: {exc}"
                )

            except Exception as exc:

                st.error(
                    f"Upload failed: {exc}"
                )


# ============================================================
# ASK DOCUMENTS PAGE
# ============================================================

if navigation == "Ask Documents":

    st.divider()

    st.header("Ask Your Documents")

    st.write(
        "Ask a question and retrieve the most relevant "
        "document chunks before generating an answer."
    )

    document_options = ["All documents"]

    document_options.extend(
        document.get(
            "filename",
            "Unknown document",
        )
        for document in documents
    )

    selected_document = st.selectbox(
        "Document scope",
        document_options,
    )

    question = st.text_area(
        "Question",
        placeholder=(
            "Ask a question about your documents..."
        ),
        height=120,
    )

    retrieved_chunks = st.slider(
        "Relevant chunks",
        min_value=1,
        max_value=20,
        value=5,
    )

    if st.button(
        "Ask Question",
        type="primary",
    ):

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            payload = {
                "question": question.strip(),
                "limit": retrieved_chunks,
            }

            if selected_document != "All documents":

                selected_id = None

                for document in documents:

                    if (
                        document.get("filename")
                        == selected_document
                    ):

                        selected_id = document.get(
                            "id"
                        )
                        break

                if selected_id is not None:
                    payload["document_id"] = selected_id

            try:

                with st.spinner(
                    "Retrieving relevant context..."
                ):

                    result = api_post(
                        "/query",
                        payload,
                    )

                st.divider()

                # ====================================================
                # ANSWER
                # ====================================================

                st.header("Answer")

                answer = result.get(
                    "answer",
                    "No answer returned.",
                )

                st.info(answer)

                # ====================================================
                # SOURCES
                # ====================================================

                sources = result.get(
                    "sources",
                    [],
                )

                st.header("Sources")

                if not sources:

                    st.caption(
                        "No sources were returned."
                    )

                else:

                    for index, source in enumerate(
                        sources,
                        start=1,
                    ):

                        filename = source.get(
                            "filename",
                            source.get(
                                "document",
                                "Unknown document",
                            ),
                        )

                        page = source.get(
                            "page",
                            source.get(
                                "page_number",
                                "—",
                            ),
                        )

                        score = source.get(
                            "score",
                            source.get(
                                "relevance",
                                None,
                            ),
                        )

                        if isinstance(
                            score,
                            (int, float),
                        ):

                            score_text = (
                                f"{score:.3f}"
                            )

                        else:

                            score_text = "—"

                        with st.container(
                            border=True
                        ):

                            source_col1, source_col2 = (
                                st.columns([5, 2])
                            )

                            with source_col1:

                                st.write(
                                    f"**{index}. "
                                    f"📄 {filename}**"
                                )

                                st.caption(
                                    f"Page {page}"
                                )

                            with source_col2:

                                st.caption(
                                    "Relevance"
                                )

                                st.write(
                                    score_text
                                )

            except requests.HTTPError as exc:

                st.error(
                    f"Query failed: {exc}"
                )

            except Exception as exc:

                st.error(
                    f"Query failed: {exc}"
                )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "RAG Pipeline • Document Intelligence"
)
