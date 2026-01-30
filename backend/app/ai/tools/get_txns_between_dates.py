"""
Tool: Get Transactions Between Dates

Retrieves transactions within a specific date range or on a specific date.
Use when user asks about transactions for a particular time period.
"""

import logging
from datetime import date, datetime
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
Get transactions within a specific date range or on a specific date.

Use this tool when the user:
- Asks about transactions on a specific date
- Wants to see transactions between two dates
- Asks "What did I spend last week?"
- Asks "Show me transactions from January"
- Asks "What were my expenses between March 1 and March 15?"
- Asks "What did I buy yesterday?"
- Asks "Show me all transactions from 2024"

Date formats supported:
- ISO format: "2024-01-15"
- Natural language dates will be converted to ISO format before calling

This tool is flexible - if only start_date is provided, it shows transactions
from that date to today. If both dates are the same, it shows transactions
for that single day.
"""

# =============================================================================
# Helper Functions
# =============================================================================


def parse_date_string(date_str: str) -> date:
    """
    Parse a date string in various formats to a date object.
    
    Args:
        date_str: Date string in ISO format (YYYY-MM-DD) or other common formats
        
    Returns:
        date object
        
    Raises:
        ValueError: If date string cannot be parsed
    """
    # Try common date formats
    formats = [
        "%Y-%m-%d",  # ISO format: 2024-01-15
        "%Y/%m/%d",  # 2024/01/15
        "%m/%d/%Y",  # 01/15/2024
        "%m-%d-%Y",  # 01-15-2024
        "%d-%m-%Y",  # 15-01-2024 (European)
        "%Y%m%d",    # 20240115
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse date string: {date_str}")


# =============================================================================
# Tool Implementation
# =============================================================================


@tool
@register_tool
def get_transactions_between_dates(
    start_date: str,
    end_date: str | None = None,
    limit: int = 50
) -> dict[str, Any]:
    """Get transactions between two dates or on a specific date.
    
    Args:
        start_date: Start date in ISO format (YYYY-MM-DD) or the specific date to query
        end_date: End date in ISO format (YYYY-MM-DD). If not provided, defaults to today
        limit: Maximum number of transactions to return (default: 50)
    
    Returns:
        Dictionary with date range info and list of transactions:
        {
            "start_date": str,
            "end_date": str,
            "transactions": list[dict],
            "total_amount": float,
            "transaction_count": int,
            "category_breakdown": dict[str, float],
            "daily_average": float
        }
    """
    logger.info(f"Tool called: get_transactions_between_dates(start_date={start_date}, end_date={end_date}, limit={limit})")
    
    try:
        session = get_session()
        user_id = get_user_id()
        
        # Parse dates
        try:
            start = parse_date_string(start_date)
        except ValueError as e:
            logger.error(f"Invalid start_date format: {start_date}")
            return {
                "error": "Invalid date format",
                "message": f"Could not parse start_date '{start_date}'. Please use YYYY-MM-DD format.",
                "transactions": [],
                "transaction_count": 0,
                "total_amount": 0.0
            }
        
        # If end_date not provided, use today
        if end_date:
            try:
                end = parse_date_string(end_date)
            except ValueError as e:
                logger.error(f"Invalid end_date format: {end_date}")
                return {
                    "error": "Invalid date format",
                    "message": f"Could not parse end_date '{end_date}'. Please use YYYY-MM-DD format.",
                    "transactions": [],
                    "transaction_count": 0,
                    "total_amount": 0.0
                }
        else:
            end = date.today()
        
        # Ensure start is before or equal to end
        if start > end:
            logger.warning(f"start_date ({start}) is after end_date ({end}), swapping")
            start, end = end, start
        
        logger.info(f"Querying transactions for user={user_id}, date_range={start} to {end}")
        
        # Query transactions within date range
        txn_query = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.auth_date >= start)
            .where(Transaction.auth_date <= end)
            .where(Transaction.pending == False)
            .order_by(Transaction.auth_date.desc())
            .limit(limit)
        )
        
        transactions = session.exec(txn_query).all()
        
        if not transactions:
            logger.warning(f"No transactions found between {start} and {end}")
            return {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "transactions": [],
                "transaction_count": 0,
                "total_amount": 0.0,
                "category_breakdown": {},
                "daily_average": 0.0,
                "message": f"No transactions found between {start} and {end}."
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
        
        # Calculate category breakdown
        category_totals: dict[str, float] = {}
        for txn in transactions:
            category = txn.category if txn.category else "Uncategorized"
            category_totals[category] = category_totals.get(category, 0.0) + txn.amount
        
        # Sort categories by amount
        category_breakdown = dict(sorted(category_totals.items(), key=lambda x: x[1], reverse=True))
        
        # Calculate daily average
        days_in_range = (end - start).days + 1  # +1 to include both start and end days
        daily_average = total_amount / days_in_range if days_in_range > 0 else 0.0
        
        # Get total count (not limited)
        count_query = (
            select(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.auth_date >= start)
            .where(Transaction.auth_date <= end)
            .where(Transaction.pending == False)
        )
        
        total_count = session.exec(count_query).one()
        
        logger.info(f"Retrieved {len(formatted_transactions)} transactions between {start} and {end}, total: ${total_amount:.2f}")
        
        return {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "days_in_range": days_in_range,
            "transactions": formatted_transactions,
            "transaction_count": len(formatted_transactions),
            "total_transaction_count": int(total_count),
            "total_amount": round(total_amount, 2),
            "daily_average": round(daily_average, 2),
            "category_breakdown": {k: round(v, 2) for k, v in category_breakdown.items()},
            "showing_limited": len(formatted_transactions) < total_count
        }
        
    except Exception as e:
        logger.error(f"Error in get_transactions_between_dates: {e}", exc_info=True)
        return {
            "start_date": start_date,
            "end_date": end_date or "today",
            "transactions": [],
            "transaction_count": 0,
            "total_amount": 0.0,
            "category_breakdown": {},
            "error": str(e),
            "message": "An error occurred while retrieving transactions."
        }
