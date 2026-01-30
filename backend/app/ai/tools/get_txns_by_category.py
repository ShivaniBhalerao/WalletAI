"""
Tool: Get Transactions by Category

Retrieves transactions filtered by spending category (food, travel, shopping, etc.).
Use when user asks about spending in a specific category.
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
Get transactions for a specific spending category.

Use this tool when the user:
- Asks about spending in a specific category
- Wants to see food/dining/restaurant transactions
- Asks "How much did I spend on groceries?"
- Asks "Show me my travel expenses"
- Asks "What did I spend on entertainment?"

Common categories include:
- Food and Drink (Groceries, Restaurants, Coffee Shops)
- Travel (Gas Stations, Public Transportation, Airlines, Hotels)
- Shopping (Clothing, Electronics, General Merchandise)
- Entertainment (Movies, Events, Recreation)
- Bills and Utilities
- Healthcare
- Personal Care
- Home Improvement

This tool returns detailed transaction information grouped by the specified category.
"""

# =============================================================================
# Tool Implementation
# =============================================================================


@tool
@register_tool
def get_transactions_by_category(
    category: str,
    limit: int = 20,
    days_back: int = 30
) -> dict[str, Any]:
    """Get transactions for a specific spending category (food, travel, shopping).
    
    Args:
        category: The spending category to filter by (e.g., "food", "travel", "groceries")
        limit: Maximum number of transactions to return (default: 20)
        days_back: Number of days to look back (default: 30)
    
    Returns:
        Dictionary with category info and list of transactions:
        {
            "category": str,
            "transactions": list[dict],
            "total_amount": float,
            "transaction_count": int,
            "top_merchants": list[dict],
            "date_range": {"start": date, "end": date}
        }
    """
    logger.info(f"Tool called: get_transactions_by_category(category={category}, limit={limit}, days_back={days_back})")
    
    try:
        session = get_session()
        user_id = get_user_id()
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Normalize category for flexible matching
        category_normalized = category.lower().strip()
        
        logger.info(f"Querying transactions for user={user_id}, category={category_normalized}, date_range={start_date} to {end_date}")
        
        # Query transactions with category filter
        # Using ILIKE for case-insensitive partial matching
        txn_query = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.category.ilike(f"%{category_normalized}%"))
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
            .order_by(Transaction.auth_date.desc())
            .limit(limit)
        )
        
        transactions = session.exec(txn_query).all()
        
        if not transactions:
            logger.warning(f"No transactions found for category: {category}")
            return {
                "category": category,
                "transactions": [],
                "transaction_count": 0,
                "total_amount": 0.0,
                "top_merchants": [],
                "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "message": f"No transactions found in category '{category}' for the specified period."
            }
        
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
            }
            for txn in transactions
        ]
        
        # Get top merchants for this category (for additional insights)
        merchant_query = (
            select(
                Transaction.merchant_name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count")
            )
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.category.ilike(f"%{category_normalized}%"))
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
            .group_by(Transaction.merchant_name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
        )
        
        merchant_results = session.exec(merchant_query).all()
        top_merchants = [
            {
                "merchant": row.merchant_name,
                "total_spent": round(float(row.total), 2),
                "transaction_count": int(row.count)
            }
            for row in merchant_results
        ]
        
        logger.info(f"Retrieved {len(formatted_transactions)} transactions in category '{category}', total: ${total_amount:.2f}")
        
        return {
            "category": category,
            "transactions": formatted_transactions,
            "transaction_count": len(formatted_transactions),
            "total_amount": round(total_amount, 2),
            "top_merchants": top_merchants,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_transactions_by_category: {e}", exc_info=True)
        return {
            "category": category,
            "transactions": [],
            "transaction_count": 0,
            "total_amount": 0.0,
            "top_merchants": [],
            "error": str(e),
            "message": "An error occurred while retrieving transactions."
        }
