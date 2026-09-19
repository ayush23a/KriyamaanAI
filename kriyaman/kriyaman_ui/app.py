import json
import os
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Streamlit Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Kriyamaan Agentic RAG",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API base URL (defaults to an environment variable or the local API server)
API_BASE_URL = os.getenv("KRIYAMAN_API_URL", "http://localhost:8000/api/v1")


def check_api_health(base_url: str) -> dict | None:
    try:
        resp = requests.get(f"{base_url}/health", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def create_session(base_url: str, title: str | None = None) -> dict | None:
    try:
        payload = {"title": title, "metadata": {}}
        resp = requests.post(f"{base_url}/sessions", json=payload, timeout=5)
        if resp.status_code in [200, 201]:
            return resp.json()
    except Exception as e:
        st.sidebar.error(f"Error creating session: {e}")
    return None


def get_session(base_url: str, session_id: str) -> dict | None:
    try:
        resp = requests.get(f"{base_url}/sessions/{session_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def upload_document(base_url: str, session_id: str, file) -> dict | None:
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        resp = requests.post(f"{base_url}/sessions/{session_id}/documents", files=files, timeout=60)
        if resp.status_code in [200, 201]:
            return resp.json()
        else:
            st.error(f"Upload failed: {resp.text}")
    except Exception as e:
        st.error(f"Upload error: {e}")
    return None


def list_documents(base_url: str, session_id: str) -> list[dict]:
    try:
        resp = requests.get(f"{base_url}/sessions/{session_id}/documents", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("documents", [])
    except Exception:
        pass
    return []


def delete_document(base_url: str, document_id: str) -> bool:
    try:
        resp = requests.delete(f"{base_url}/documents/{document_id}", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def create_memory(base_url: str, session_id: str, content: str, kind: str = "user_preference") -> dict | None:
    try:
        payload = {"content": content, "kind": kind}
        resp = requests.post(f"{base_url}/sessions/{session_id}/memories", json=payload, timeout=5)
        if resp.status_code in [200, 201]:
            return resp.json()
    except Exception as e:
        st.error(f"Memory save error: {e}")
    return None


def list_memories(base_url: str, session_id: str) -> list[dict]:
    try:
        resp = requests.get(f"{base_url}/sessions/{session_id}/memories", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("memories", [])
    except Exception:
        pass
    return []


def delete_memory(base_url: str, memory_id: str) -> bool:
    try:
        resp = requests.delete(f"{base_url}/memories/{memory_id}", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def run_query(
    base_url: str,
    session_id: str,
    query: str,
    enable_web: bool = False,
    max_iterations: int = 3,
) -> dict | None:
    try:
        payload = {
            "query": query,
            "enable_web_search": enable_web,
            "budgets": {
                "max_retrieval_iterations": max_iterations,
                "max_tool_calls": 3,
                "max_latency_ms": 30000,
                "max_input_tokens": 12000,
                "max_output_tokens": 2000,
            },
        }
        resp = requests.post(f"{base_url}/sessions/{session_id}/runs", json=payload, timeout=60)
        if resp.status_code in [200, 201]:
            return resp.json()
        else:
            st.error(f"Run failed: {resp.text}")
    except Exception as e:
        st.error(f"Query execution error: {e}")
    return None


def get_run_events(base_url: str, run_id: str) -> list[dict]:
    try:
        resp = requests.get(f"{base_url}/runs/{run_id}/events", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("events", [])
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Sidebar UI
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚡ Kriyamaan Agentic RAG")
    api_url = st.text_input("Backend API URL", value=API_BASE_URL)

    # Health Indicator
    health_data = check_api_health(api_url)
    if health_data:
        st.success(f"Backend: {health_data.get('status', 'healthy').upper()} (v{health_data.get('version', '1.0.0')})")
        with st.expander("System Dependencies"):
            for dep, stat in health_data.get("dependencies", {}).items():
                st.write(f"- **{dep}**: `{stat}`")
    else:
        st.warning("Backend API unreachable at specified URL.")

    st.divider()

    # Session Management
    st.subheader("Session Management")
    if "session_id" not in st.session_state:
        st.session_state.session_id = ""

    if st.button("➕ New Session", use_container_width=True):
        new_sess = create_session(api_url, title="Streamlit Workspace")
        if new_sess:
            st.session_state.session_id = new_sess["session_id"]
            st.rerun()

    current_session = st.text_input("Active Session ID", value=st.session_state.session_id)
    if current_session != st.session_state.session_id:
        st.session_state.session_id = current_session

    st.divider()

    # Document Ingestion
    if st.session_state.session_id:
        st.subheader("Document Ingestion")
        uploaded_file = st.file_uploader(
            "Upload knowledge doc (PDF, DOCX, TXT, MD, HTML)",
            type=["pdf", "docx", "txt", "md", "html"],
        )
        if uploaded_file and st.button("Ingest Document", use_container_width=True):
            with st.spinner("Parsing, chunking, and embedding..."):
                res = upload_document(api_url, st.session_state.session_id, uploaded_file)
                if res:
                    st.success(f"Ingested '{res['name']}' ({res['chunk_count']} chunks)")
                    st.rerun()

        # List session documents
        docs = list_documents(api_url, st.session_state.session_id)
        if docs:
            st.markdown(f"**Session Documents ({len(docs)})**")
            for doc in docs:
                col1, col2 = st.columns([4, 1])
                col1.caption(f"📄 {doc['name']}")
                if col2.button("🗑️", key=f"del_doc_{doc['document_id']}"):
                    delete_document(api_url, doc["document_id"])
                    st.rerun()

        st.divider()

        # Explicit Memory Management
        st.subheader("Explicit Long-term Memory")
        mem_input = st.text_input("Add User Preference / Fact", placeholder="e.g. Prefer concise answers")
        if st.button("Save Memory", use_container_width=True) and mem_input:
            res = create_memory(api_url, st.session_state.session_id, mem_input)
            if res:
                st.success("Saved memory to principal namespace!")
                st.rerun()

        memories = list_memories(api_url, st.session_state.session_id)
        if memories:
            st.markdown(f"**Saved Memories ({len(memories)})**")
            for mem in memories:
                mcol1, mcol2 = st.columns([4, 1])
                mcol1.caption(f"🧠 {mem['content']}")
                if mcol2.button("🗑️", key=f"del_mem_{mem['memory_id']}"):
                    delete_memory(api_url, mem["memory_id"])
                    st.rerun()


# ---------------------------------------------------------------------------
# Main Content Area
# ---------------------------------------------------------------------------
if not st.session_state.session_id:
    st.info("👋 Welcome to Kriyamaan. Please create or enter a Session ID in the sidebar to begin.")
else:
    st.header("Agentic Search & Generation")

    # Options row
    opt_col1, opt_col2, opt_col3 = st.columns([2, 2, 2])
    with opt_col1:
        enable_web = st.checkbox("Enable Web Search Fallback", value=False)
    with opt_col2:
        max_iters = st.slider("Max Retrieval Iterations", min_value=1, max_value=5, value=3)
    with opt_col3:
        st.caption(f"Session: `{st.session_state.session_id[:16]}...`")

    # Query Input
    query = st.text_area("Ask a question:", placeholder="e.g. What is the return policy for defective items?", height=80)

    if st.button("Execute Query 🚀", type="primary") and query:
        with st.spinner("Executing agentic graph (Controller ➔ Retrieval ➔ Evidence Judge ➔ Gate ➔ Generation)..."):
            run_result = run_query(
                api_url,
                st.session_state.session_id,
                query=query,
                enable_web=enable_web,
                max_iterations=max_iters,
            )

        if run_result:
            status_val = run_result.get("status", "unknown")
            run_id = run_result.get("run_id", "")

            # Status Badge
            if status_val == "answer":
                st.success(f"Status: ANSWER (Terminal Gate Passed)")
            elif status_val == "clarification":
                st.warning("Status: CLARIFICATION NEEDED")
            elif status_val == "abstention":
                st.error("Status: ABSTENTION (Insufficient verified evidence)")
            elif status_val == "conflicting":
                st.warning("Status: CONFLICTING EVIDENCE DETECTED")
            else:
                st.info(f"Status: {status_val.upper()}")

            # Answer text
            ans = run_result.get("answer")
            if ans:
                st.subheader("Answer")
                st.markdown(ans.get("answer_text", ""))

                m1, m2 = st.columns(2)
                m1.metric("Confidence", f"{ans.get('confidence', 0.0):.2f}")
                m2.metric("Needs Follow-up", "Yes" if ans.get("needs_follow_up") else "No")

            # Verified Citations
            evidence = run_result.get("evidence", [])
            citations = ans.get("citation_ids", []) if ans else []
            if evidence:
                with st.expander(f"📚 Verified Evidence & Citations ({len(evidence)} items, {len(citations)} cited)"):
                    for item in evidence:
                        is_cited = item["evidence_id"] in citations
                        prefix = "✅ [CITED] " if is_cited else "📎 "
                        st.markdown(f"**{prefix}`{item['evidence_id']}`** — Method: `{item['retrieval_method']}` | Score: `{item.get('retrieval_score', 0.0):.3f}`")
                        st.info(item["content"])

            # Execution Events Replay
            events = get_run_events(api_url, run_id)
            if events:
                with st.expander(f"⚙️ Execution Events Stream ({len(events)} events)"):
                    for ev in events:
                        st.markdown(f"- **Step {ev['sequence']}** [`{ev['event_type']}`]: `{json.dumps(ev.get('payload', {}))}`")

            # Execution Metrics
            usage = run_result.get("usage") or {}
            budgets = run_result.get("budgets") or {}
            with st.expander("📊 Execution Metrics & Monotonic Budgets"):
                met_col1, met_col2, met_col3, met_col4 = st.columns(4)
                met_col1.metric("Prompt Tokens", usage.get("prompt_tokens", 0))
                met_col2.metric("Completion Tokens", usage.get("completion_tokens", 0))
                met_col3.metric("Latency", f"{usage.get('total_latency_ms', 0)} ms")
                estimated_cost = float(usage.get("estimated_cost_usd") or 0.0)
                met_col4.metric("Est. Cost", f"${estimated_cost:.4f}")

    # Recent Conversation History
    st.divider()
    sess_detail = get_session(api_url, st.session_state.session_id)
    if sess_detail and sess_detail.get("turns"):
        with st.expander(f"💬 Conversation History ({len(sess_detail['turns'])} turns)"):
            for turn in sess_detail["turns"]:
                st.markdown(f"**User**: {turn['user_query']}")
                if turn.get("answer"):
                    st.markdown(f"**Assistant**: {turn['answer'].get('answer_text')}")
                st.divider()
