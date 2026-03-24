# import streamlit as st
# import requests
# import pandas as pd

# API_URL = "http://127.0.0.1:8000" # URL của FastAPI backend

# # Session State
# def init_session(): # Khởi tạo session state để lưu db_id và lịch sử truy vấn
#     if "db_id" not in st.session_state:
#         st.session_state.db_id = None
#     if "history" not in st.session_state:
#         st.session_state.history = []

# # Parse result từ tool
# def parse_sql_result(result_str):
#     try:
#         data = eval(result_str)
#         if isinstance(data, dict) and "data" in data:
#             df = pd.DataFrame(data["data"], columns=data["columns"])
#             return df
#     except:
#         return None
#     return None

# # Call API: Load DB
# def load_database(db_id):
#     try:
#         # Gọi API để load database và tạo agent
#         res = requests.post(   
#             f"{API_URL}/load_db",
#             json={"db_id": db_id}
#         )
#         # Kiểm tra phản hồi từ API
#         if res.status_code == 200:
#             return res.json()
#         else:
#             return {"success": False, "error": res.text}

#     except Exception as e:
#         return {"success": False, "error": str(e)}

# # Call API: Query
# def run_query(question):
#     try:

#         db_id = st.session_state.db_id # Lấy db_id từ session state để gửi cùng câu hỏi

#         # Gọi API để chạy câu hỏi và lấy kết quả
#         res = requests.post(
#             f"{API_URL}/query",
#             json={
#                 "db_id": db_id,
#                 "question": question
#             }
#         )

#         # Kiểm tra phản hồi từ API
#         if res.status_code == 200:
#             data = res.json()
#             return {
#                 "success": True,
#                 "output": data["output"],
#                 "raw": data["raw"]
#             }
#         else:
#             return {
#                 "success": False,
#                 "output": res.text,
#                 "raw": None
#             }

#     except Exception as e:
#         return {
#             "success": False,
#             "output": str(e),
#             "raw": None
#         }

# # UI
# def main():
#     init_session() # Khởi tạo session state khi bắt đầu ứng dụng

#     # Cấu hình trang
#     st.set_page_config(
#         page_title="NL2SQL Agent (API)",
#         layout="wide"
#     ) 

#     # Header
#     st.title("💬 NL → SQL Agent (API version)")
#     st.caption("UI gọi FastAPI backend")

#     # Sidebar
#     with st.sidebar:
#         st.header("⚙️ Cấu hình")

#         db_id = st.text_input(
#             "Database ID",
#             placeholder="vd: E_commerce"
#         )

#         if st.button("Load Database"):
#             if db_id:
#                 result = load_database(db_id)

#                 if result.get("success"): # Nếu load database thành công, lưu db_id vào session state để sử dụng cho các truy vấn sau này
#                     st.session_state.db_id = db_id
#                     st.success(f"Loaded DB: {db_id}")
#                     st.write("Tables:", result.get("tables", []))
#                 else:
#                     st.error(result.get("error"))

#             else:
#                 st.warning("Nhập db_id")

#         st.divider() # Phân cách

#         if st.button("Clear History"):
#             st.session_state.history = []
#             st.success("Đã clear")

#     # Main
#     if st.session_state.db_id is None:
#         st.info("👉 Nhập db_id và load database trước")
#         return

#     question = st.text_area(
#         "Nhập câu hỏi:",
#         placeholder="VD: Top 5 khách hàng mua nhiều nhất?",
#         height=100
#     )

#     if st.button("🚀 Run", type="primary"):
#         if not question.strip():
#             st.warning("Nhập câu hỏi trước")
#         else:
#             result = run_query(question)

#             st.session_state.history.append({
#                 "question": question,
#                 "result": result
#             })

#             st.divider()
#             st.subheader("📌 Kết quả")

#             if result["success"]:
#                 st.success("Thành công")

#                 st.markdown("### 💬 Trả lời")
#                 st.write(result["output"])

#                 # nếu là table thì show dataframe
#                 df = parse_sql_result(result["output"])
#                 if df is not None:
#                     st.dataframe(df)

#                 with st.expander("🧠 Agent Trace (debug)"):
#                     st.json(result["raw"])

#             else:
#                 st.error(result["output"])

#     # History
#     if st.session_state.history:
#         st.divider()
#         st.subheader("📜 Lịch sử")

#         for i, item in enumerate(reversed(st.session_state.history), 1):
#             with st.expander(f"Query {i}: {item['question'][:50]}"):
#                 st.write("**Question:**", item["question"])
#                 st.write("**Answer:**", item["result"]["output"])


# if __name__ == "__main__":
#     main()

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

    except Exception as e:
        logger.error("Failed to initialize session state", exc_info=True)
        raise RuntimeError(f"Session initialization failed: {str(e)}") from e


# -------------------------------------------------------------------
# UTILS
# -------------------------------------------------------------------

def parse_sql_result(result_str: str) -> Optional[pd.DataFrame]:
    """
    Parse SQL result string into a Pandas DataFrame.

    Args:
        result_str (str): String representation of SQL result.

    Returns:
        Optional[pd.DataFrame]: DataFrame if parsing is successful, else None.
    """
    try:
        data = eval(result_str)  # ⚠️ kept original logic intentionally

        if isinstance(data, dict) and "data" in data:
            df = pd.DataFrame(data["data"], columns=data["columns"])
            return df

    except Exception as e:
        logger.warning("Failed to parse SQL result: %s", str(e))

    return None


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
                "question": question
            }
        )

        if res.status_code == 200:
            data = res.json()

            return {
                "success": True,
                "output": data["output"],
                "raw": data["raw"]
            }

        logger.error("API /query failed: %s", res.text)
        return {
            "success": False,
            "output": res.text,
            "raw": None
        }

    except Exception as e:
        logger.error("Error calling /query API", exc_info=True)
        return {
            "success": False,
            "output": str(e),
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
            page_title="NL2SQL Agent (API)",
            layout="wide"
        )

        # Header
        st.title("💬 NL → SQL Agent (API version)")
        st.caption("UI gọi FastAPI backend")

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

            if st.button("Clear History"):
                st.session_state.history = []
                st.success("Đã clear")

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

                    st.markdown("### 💬 Trả lời")
                    st.write(result["output"])

                    df = parse_sql_result(result["output"])
                    if df is not None:
                        st.dataframe(df)

                    with st.expander("🧠 Agent Trace (debug)"):
                        st.json(result["raw"])

                else:
                    st.error(result["output"])

        # History
        if st.session_state.history:
            st.divider()
            st.subheader("📜 Lịch sử")

            for i, item in enumerate(reversed(st.session_state.history), 1):
                with st.expander(f"Query {i}: {item['question'][:50]}"):
                    st.write("**Question:**", item["question"])
                    st.write("**Answer:**", item["result"]["output"])

    except Exception as e:
        logger.error("Streamlit app failed", exc_info=True)
        raise RuntimeError(f"Streamlit app error: {str(e)}") from e


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------

if __name__ == "__main__":
    main()