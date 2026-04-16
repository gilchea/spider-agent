###routers/app.py
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

from src.handlers.logging_config import logger


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
            page_title="NL2SQL Chatbot",
            layout="centered",
            page_icon="💬"
        )

        # Sidebar
        with st.sidebar:
            st.title("⚙️ Configuration")
            
            db_id = st.text_input(
                "Database ID",
                value=st.session_state.db_id if st.session_state.db_id else "",
                placeholder="e.g., school_scheduling"
            )

            if st.button("Load Database", use_container_width=True):
                if db_id:
                    with st.spinner("Loading database..."):
                        result = load_database(db_id)
                        if result.get("success"):
                            st.session_state.db_id = db_id
                            st.success(f"Successfully loaded: {db_id}")
                            # Optional: Clear history when switching DB
                            # st.session_state.history = []
                        else:
                            st.error(f"Error: {result.get('error')}")
                else:
                    st.warning("Please enter a Database ID")

            st.divider()
            
            if st.button("Clear Chat", use_container_width=True):
                st.session_state.history = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()

            if st.session_state.db_id:
                st.info(f"Currently connected to: **{st.session_state.db_id}**")

        # Chat Interface
        st.title("💬 NL2SQL Chatbot")
        st.markdown("Ask questions about your database in natural language.")

        if st.session_state.db_id is None:
            st.warning("👈 Please load a database in the sidebar to start chatting.")
            return

        # Display Chat History
        for chat in st.session_state.history:
            # User message
            with st.chat_message("user"):
                st.markdown(chat["question"])
            
            # Assistant response
            with st.chat_message("assistant"):
                res = chat["result"]
                if res["success"]:
                    st.markdown(res["answer"])
                    
                    if res.get("data") and res.get("columns"):
                        df = pd.DataFrame(res["data"], columns=res["columns"])
                        st.dataframe(df, hide_index=True)
                    
                    if res.get("execution_time"):
                        st.caption(f"⏱️ Execution time: {res['execution_time']}s")
                    
                    with st.expander("🔍 Trace & Debug"):
                        st.json(res["raw"])
                else:
                    st.error(res.get("answer", "Unknown error occurred"))

        # Chat Input
        if prompt := st.chat_input("Ask a question about your data..."):
            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(prompt)

            # Call API
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    result = run_query(prompt)
                    
                    if result["success"]:
                        st.markdown(result["answer"])
                        if result.get("data") and result.get("columns"):
                            df = pd.DataFrame(result["data"], columns=result["columns"])
                            st.dataframe(df, hide_index=True)
                        
                        if result.get("execution_time"):
                            st.caption(f"⏱️ Execution time: {result['execution_time']}s")
                        
                        with st.expander("🔍 Trace & Debug"):
                            st.json(result["raw"])
                    else:
                        st.error(result.get("answer", "Error executing query"))

            # Append to history
            st.session_state.history.append({
                "question": prompt,
                "result": result
            })
            
            # st.rerun() # Not strictly necessary with chat_input usually, but keeps state synced

    except Exception as e:
        logger.error("Streamlit app failed", exc_info=True)
        st.error(f"An unexpected error occurred: {str(e)}")

# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------

if __name__ == "__main__":
    main()