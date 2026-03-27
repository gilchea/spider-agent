"""
Streamlit UI module for NL2SQL API system.

This module provides a web-based interface for interacting with the NL2SQL API.
It allows users to:
- Load a database
- Submit natural language queries
- View results and execution traces
- Track query history

The UI communicates with a FastAPI backend.
"""

import streamlit as st
import requests
import pandas as pd
from typing import Optional, Dict, Any
import uuid

from src.helpers.logging_config import logger


API_URL = "http://127.0.0.1:8000"


# -------------------------------------------------------------------
# SESSION MANAGEMENT
# -------------------------------------------------------------------

def init_session() -> None:
    """
    Initialize Streamlit session state.

    This function ensures required session variables exist.

    Raises:
        RuntimeError: If session initialization fails.
    """
    try:
        if "db_id" not in st.session_state:
            st.session_state.db_id = None

        if "history" not in st.session_state:
            st.session_state.history = []

        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())

    except Exception as e:
        logger.error("Failed to initialize session state", exc_info=True)
        raise RuntimeError(f"Session initialization failed: {str(e)}") from e

# -------------------------------------------------------------------
# API CLIENT
# -------------------------------------------------------------------

def load_database(db_id: str) -> Dict[str, Any]:
    """
    Call API to load database and initialize agent.

    Args:
        db_id (str): Database identifier.

    Returns:
        Dict[str, Any]: API response.

    Raises:
        RuntimeError: If API call fails.
    """
    try:
        logger.info("Calling /load_db API with db_id: %s", db_id)

        res = requests.post(
            f"{API_URL}/load_db",
            json={"db_id": db_id}
        )

        if res.status_code == 200:
            return res.json()

        logger.error("API /load_db failed: %s", res.text)
        return {"success": False, "error": res.text}

    except Exception as e:
        logger.error("Error calling /load_db API", exc_info=True)
        return {"success": False, "error": str(e)}


def run_query(question: str) -> Dict[str, Any]:
    """
    Call API to execute a natural language query.

    Args:
        question (str): User question.

    Returns:
        Dict[str, Any]: Query result including output and raw trace.

    Raises:
        RuntimeError: If API call fails.
    """
    try:
        db_id = st.session_state.db_id

        logger.info(
            "Calling /query API | db_id: %s | question: %s",
            db_id,
            question
        )

        res = requests.post(
            f"{API_URL}/query",
            json={
                "db_id": db_id,
                "question": question,
                "session_id": st.session_state.session_id
            }
        )

        if res.status_code == 200:
            data = res.json()
            return {
                "success": True,
                "answer": data.get("answer"),
                "data": data.get("data"),
                "columns": data.get("columns"),
                "raw": data.get("raw"),
                "execution_time": data.get("execution_time")
            }

        elif res.status_code == 429:
            return {
                "success": False,
                "answer": "🚫 Hết quota LLM, thử lại sau",
                "raw": None
            }

        elif res.status_code == 503:
            return {
                "success": False,
                "answer": "⚠️ Model đang quá tải",
                "raw": None
            }

        elif res.status_code == 504:
            return {
                "success": False,
                "answer": "⏳ Model phản hồi quá chậm (timeout)",
                "raw": None
            }

        else:
            return {
                "success": False,
                "answer": "💥 Lỗi server",
                "raw": None
            }

    except Exception as e:
        logger.error("Error calling /query API", exc_info=True)
        return {
            "success": False,
            "answer": str(e),
            "raw": None
        }


# -------------------------------------------------------------------
# UI
# -------------------------------------------------------------------

def main() -> None:
    """
    Main entry point for Streamlit application.

    This function handles:
    - UI rendering
    - User interactions
    - API communication
    - Displaying results and history

    Raises:
        RuntimeError: If UI rendering fails.
    """
    try:
        init_session()

        # Page config
        st.set_page_config(
            page_title="NL2SQL Agent",
            layout="wide"
        )

        # Header
        st.title("💬 NL → SQL Agent")
        st.caption("Streamlit UI for NL2SQL API system")

        # Sidebar
        with st.sidebar:
            st.header("⚙️ Cấu hình")

            db_id = st.text_input(
                "Database ID",
                placeholder="vd: E_commerce"
            )

            if st.button("Load Database"):
                if db_id:
                    result = load_database(db_id)

                    if result.get("success"):
                        st.session_state.db_id = db_id
                        st.success(f"Loaded DB: {db_id}")
                        st.write("Tables:", result.get("tables", []))
                    else:
                        st.error(result.get("error"))
                else:
                    st.warning("Nhập db_id")

            st.divider()

            # if st.button("Clear History"):
            #     st.session_state.history = []
            #     st.success("Đã clear")
            if st.button("Clear History"):
                st.session_state.history = []
                st.session_state.session_id = str(uuid.uuid4())  # 👈 reset memory
                st.success("Đã clear (UI + Memory)")

        # Main
        if st.session_state.db_id is None:
            st.info("👉 Nhập db_id và load database trước")
            return

        question = st.text_area(
            "Nhập câu hỏi:",
            placeholder="VD: Top 5 khách hàng mua nhiều nhất?",
            height=100
        )

        if st.button("🚀 Run", type="primary"):
            if not question.strip():
                st.warning("Nhập câu hỏi trước")
            else:
                result = run_query(question)

                st.session_state.history.append({
                    "question": question,
                    "result": result
                })

                st.divider()
                st.subheader("📌 Kết quả")

                if result["success"]:
                    st.success("Thành công")

                    st.caption(f"⏱️ Thời gian chạy: {result.get('execution_time')} giây")

                    st.markdown("### 💬 Trả lời")

                    st.write(result.get("answer")) # text trả lời

                    df = None

                    if result.get("data") and result.get("columns"):
                        df = pd.DataFrame(
                            result["data"],
                            columns=result["columns"]
                        )
                        st.dataframe(df)

                    with st.expander("🧠 Agent Trace (debug)"): 
                        st.json(result["raw"])

                else:
                    st.error(result.get("answer"))

        # History
        if st.session_state.history:
            st.divider()
            st.subheader("📜 Lịch sử")

            for i, item in enumerate(reversed(st.session_state.history), 1):
                with st.expander(f"Query {i}: {item['question'][:50]}"):
                    st.write("**Question:**", item["question"])
                    st.write("**Answer:**", item["result"].get("answer"))

    except Exception as e:
        logger.error("Streamlit app failed", exc_info=True)
        raise RuntimeError(f"Streamlit app error: {str(e)}") from e

# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------

if __name__ == "__main__":
    main()