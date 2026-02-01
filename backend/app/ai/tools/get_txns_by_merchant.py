"""
Tool: Get Transactions by Merchant

Retrieves transactions filtered by merchant/store name (McDonald's, Starbucks, Amazon, etc.).
Use when user asks about spending at a specific merchant or store.
"""

import logging
from datetime import date, timedelta
from typing import Any

from langchain_core.tools import tool
from sqlmodel import func, select

from app.ai.tools.base import get_session, get_user_id, register_tool
from app.models import Account, Transaction

logger = logging.getLogger(__name__)

# =============================================================================
# Tool Prompt - Used by LLM to understand when to use this tool
# =============================================================================

TOOL_DESCRIPTION = """
Get transactions for a specific merchant or store.

Use this tool when the user:
- Asks about spending at a specific merchant/store
- Wants to see transactions from a particular business
- Asks "How much did I spend at Starbucks?"
- Asks "Show me my Amazon purchases"
- Asks "What did I buy at Walmart?"
- Asks "How many times did I go to McDonald's?"

Common merchants include:
- Restaurants: McDonald's, Starbucks, Chipotle, Panera
- Retail: Amazon, Walmart, Target, Costco
- Gas: Shell, Chevron, BP, Exxon
- Grocery: Whole Foods, Trader Joe's, Safeway
- Online: Amazon, eBay, Etsy

This tool returns all transactions from the specified merchant with detailed
information about amounts, dates, and categories.
"""

# =============================================================================
# Tool Implementation
# =============================================================================


@tool
@register_tool
def get_transactions_by_merchant(
    merchant_name: str,
    limit: int = 20,
    days_back: int = 90
) -> dict[str, Any]:
    """Get transactions for a specific merchant/store (McDonald's, Amazon, Starbucks).
    
    Args:
        merchant_name: The name of the merchant/store to filter by
        limit: Maximum number of transactions to return (default: 20)
        days_back: Number of days to look back (default: 90 for merchant history)
    
    Returns:
        Dictionary with merchant info and list of transactions:
        {
            "merchant_name": str,
            "transactions": list[dict],
            "total_amount": float,
            "transaction_count": int,
            "average_amount": float,
            "categories": list[str],
            "date_range": {"start": date, "end": date}
        }
    """
    logger.info(f"Tool called: get_transactions_by_merchant(merchant_name={merchant_name}, limit={limit}, days_back={days_back})")
    
    try:
        session = get_session()
        user_id = get_user_id()
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Normalize merchant name for flexible matching
        merchant_normalized = merchant_name.lower().strip()
        
        logger.info(f"Querying transactions for user={user_id}, merchant={merchant_normalized}, date_range={start_date} to {end_date}")
        
        # Query transactions with merchant filter
        # Using ILIKE for case-insensitive partial matching
        txn_query = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.merchant_name.ilike(f"%{merchant_normalized}%"))
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
            .order_by(Transaction.auth_date.desc())
            .limit(limit)
        )
        
        transactions = session.exec(txn_query).all()
        
        if not transactions:
            logger.warning(f"No transactions found for merchant: {merchant_name}")
            return {
                "merchant_name": merchant_name,
                "transactions": [],
                "transaction_count": 0,
                "total_amount": 0.0,
                "average_amount": 0.0,
                "categories": [],
                "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "message": f"No transactions found for merchant '{merchant_name}' in the specified period."
            }
        
        # Calculate statistics
        total_amount = sum(txn.amount for txn in transactions)
        average_amount = total_amount / len(transactions) if transactions else 0.0
        
        # Extract unique categories
        categories = list(set(txn.category for txn in transactions if txn.category))
        
        # Format transactions for response
        formatted_transactions = [
            {
                "id": str(txn.id),
                "amount": float(txn.amount),
                "date": txn.auth_date.isoformat(),
                "merchant": txn.merchant_name,
                "category": txn.category,
            }
            for txn in transactions
        ]
        
        # Get total count (not limited) for summary
        count_query = (
            select(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.merchant_name.ilike(f"%{merchant_normalized}%"))
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
        )
        
        total_count = session.exec(count_query).one()
        
        logger.info(f"Retrieved {len(formatted_transactions)} transactions for merchant '{merchant_name}', total: ${total_amount:.2f}")
        
        return {
            "merchant_name": merchant_name,
            "transactions": formatted_transactions,
            "transaction_count": len(formatted_transactions),
            "total_transaction_count": int(total_count),
            "total_amount": round(total_amount, 2),
            "average_amount": round(average_amount, 2),
            "categories": categories,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "showing_limited": len(formatted_transactions) < total_count
        }
        
    except Exception as e:
        logger.error(f"Error in get_transactions_by_merchant: {e}", exc_info=True)
        return {
            "merchant_name": merchant_name,
            "transactions": [],
            "transaction_count": 0,
            "total_amount": 0.0,
            "average_amount": 0.0,
            "categories": [],
            "error": str(e),
            "message": "An error occurred while retrieving transactions."
        }
