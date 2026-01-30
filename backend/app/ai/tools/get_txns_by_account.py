"""
Tool: Get Transactions by Account

Retrieves transactions filtered by account type (checking, savings, credit, etc.).
Use when user asks about spending or transactions in a specific account.
"""

import logging
from datetime import date, timedelta
from typing import Any

from langchain_core.tools import tool
from sqlmodel import select

from app.ai.tools.base import get_session, get_user_id, register_tool
from app.models import Account, Transaction

logger = logging.getLogger(__name__)

# =============================================================================
# Tool Prompt - Used by LLM to understand when to use this tool
# =============================================================================

TOOL_DESCRIPTION = """
Get transactions for a specific account type.

Use this tool when the user:
- Asks about transactions in their checking/savings/credit account
- Wants to see spending from a specific account
- Asks "What did I spend from my savings account?"
- Asks "Show me my checking account transactions"
- Asks "How much did I spend from my credit card?"

Account types include: checking, savings, credit, investment, loan, depository

This tool returns detailed transaction information including amounts, merchants,
categories, and dates for the specified account type.
"""

# =============================================================================
# Tool Implementation
# =============================================================================


@tool
@register_tool
def get_transactions_by_account(
    account_type: str,
    limit: int = 20,
    days_back: int = 30
) -> dict[str, Any]:
    """Get transactions for a specific account type (checking, savings, credit).
    
    Args:
        account_type: The type of account (checking, savings, credit, investment, loan, depository)
        limit: Maximum number of transactions to return (default: 20)
        days_back: Number of days to look back (default: 30)
    
    Returns:
        Dictionary with account info and list of transactions:
        {
            "account_type": str,
            "accounts_found": int,
            "transactions": list[dict],
            "total_amount": float,
            "date_range": {"start": date, "end": date}
        }
    """
    logger.info(f"Tool called: get_transactions_by_account(account_type={account_type}, limit={limit}, days_back={days_back})")
    
    try:
        session = get_session()
        user_id = get_user_id()
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Normalize account type for flexible matching
        account_type_normalized = account_type.lower().strip()
        
        logger.info(f"Querying transactions for user={user_id}, account_type={account_type_normalized}, date_range={start_date} to {end_date}")
        
        # First, find accounts of the specified type for this user
        account_query = (
            select(Account)
            .where(Account.user_id == user_id)
            .where(Account.type.ilike(f"%{account_type_normalized}%"))
        )
        
        accounts = session.exec(account_query).all()
        
        if not accounts:
            logger.warning(f"No accounts found for type: {account_type}")
            return {
                "account_type": account_type,
                "accounts_found": 0,
                "transactions": [],
                "total_amount": 0.0,
                "date_range": {"start": start_date, "end": end_date},
                "message": f"No {account_type} accounts found for this user."
            }
        
        account_ids = [account.id for account in accounts]
        logger.info(f"Found {len(accounts)} accounts of type '{account_type}'")
        
        # Query transactions for these accounts
        txn_query = (
            select(Transaction)
            .where(Transaction.account_id.in_(account_ids))
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
            .order_by(Transaction.auth_date.desc())
            .limit(limit)
        )
        
        transactions = session.exec(txn_query).all()
        
        # Calculate total amount
        total_amount = sum(txn.amount for txn in transactions)
        
        # Format transactions for response
        formatted_transactions = [
            {
                "id": str(txn.id),
                "amount": float(txn.amount),
                "date": txn.auth_date.isoformat(),
                "merchant": txn.merchant_name,
                "category": txn.category,
                "account_id": str(txn.account_id),
            }
            for txn in transactions
        ]
        
        logger.info(f"Retrieved {len(formatted_transactions)} transactions, total amount: ${total_amount:.2f}")
        
        return {
            "account_type": account_type,
            "accounts_found": len(accounts),
            "account_names": [acc.name for acc in accounts],
            "transactions": formatted_transactions,
            "transaction_count": len(formatted_transactions),
            "total_amount": round(total_amount, 2),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_transactions_by_account: {e}", exc_info=True)
        return {
            "account_type": account_type,
            "accounts_found": 0,
            "transactions": [],
            "total_amount": 0.0,
            "error": str(e),
            "message": "An error occurred while retrieving transactions."
        }
