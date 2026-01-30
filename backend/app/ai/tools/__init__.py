"""
AI Tools Module - Transaction Query Tools

This module provides LangChain tools for querying financial transaction data.
Each tool is self-contained with its own prompt and implementation.

Tools are automatically registered on import and can be accessed via get_all_tools().
"""

# Import base utilities first
from app.ai.tools.base import (
    clear_context,
    current_session,
    current_user_id,
    get_all_tools,
    get_session,
    get_user_id,
    register_tool,
    set_context,
)

# Import all tools (this triggers their registration)
from app.ai.tools.get_txns_between_dates import get_transactions_between_dates
from app.ai.tools.get_txns_by_account import get_transactions_by_account
from app.ai.tools.get_txns_by_category import get_transactions_by_category
from app.ai.tools.get_txns_by_merchant import get_transactions_by_merchant

__all__ = [
    # Context management
    "current_session",
    "current_user_id",
    "set_context",
    "clear_context",
    "get_session",
    "get_user_id",
    # Tool registry
    "get_all_tools",
    "register_tool",
    # Transaction query tools
    "get_transactions_by_account",
    "get_transactions_by_category",
    "get_transactions_by_merchant",
    "get_transactions_between_dates",
]
