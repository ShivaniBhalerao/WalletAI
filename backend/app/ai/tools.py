"""
Tool definitions for Financial Analyst Agent

This module defines tools that the agent can use to query and analyze financial data.
Currently contains stubs for future implementation when integrating with actual database queries.
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Stubs for Future Implementation
# =============================================================================
# These functions provide the interface for tools that will be integrated
# into the LangGraph agent once database access is enabled.
# For now, they return mock data but are architected to be easily replaced
# with real database queries.
# =============================================================================


async def query_spending_by_category(
    user_id: uuid.UUID,
    category: str,
    start_date: date | None = None,
    end_date: date | None = None
) -> dict[str, Any]:
    """
    Query user's spending in a specific category for a given time period
    
    Future Implementation:
        - Query Transaction table filtered by category and date range
        - Join with Account table to ensure user ownership
        - Aggregate amounts
    
    Args:
        user_id: User's UUID
        category: Spending category (e.g., "groceries", "dining", "transportation")
        start_date: Start of date range (optional, defaults to current month start)
        end_date: End of date range (optional, defaults to today)
        
    Returns:
        Dictionary with spending data:
        {
            "category": str,
            "total_amount": float,
            "transaction_count": int,
            "start_date": date,
            "end_date": date,
            "top_merchants": list[dict]
        }
    """
    logger.info(f"[STUB] Query spending by category: user={user_id}, category={category}")
    
    # TODO: Replace with actual database query
    # Example query structure:
    # SELECT 
    #     SUM(amount) as total,
    #     COUNT(*) as count,
    #     merchant_name,
    #     COUNT(*) as merchant_count
    # FROM transaction t
    # JOIN account a ON t.account_id = a.id
    # WHERE a.user_id = :user_id
    #   AND t.category = :category
    #   AND t.auth_date BETWEEN :start_date AND :end_date
    # GROUP BY merchant_name
    # ORDER BY merchant_count DESC
    # LIMIT 3
    
    # Mock data for now
    return {
        "category": category,
        "total_amount": 342.50,
        "transaction_count": 23,
        "start_date": start_date or date.today().replace(day=1),
        "end_date": end_date or date.today(),
        "top_merchants": [
            {"name": "Whole Foods", "amount": 180.00},
            {"name": "Trader Joe's", "amount": 95.00},
            {"name": "Local Market", "amount": 67.50},
        ]
    }


async def query_spending_by_time_period(
    user_id: uuid.UUID,
    start_date: date,
    end_date: date
) -> dict[str, Any]:
    """
    Query total spending for a time period
    
    Future Implementation:
        - Query Transaction table for date range
        - Join with Account table to ensure user ownership
        - Aggregate by category
    
    Args:
        user_id: User's UUID
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        Dictionary with spending data:
        {
            "total_amount": float,
            "transaction_count": int,
            "start_date": date,
            "end_date": date,
            "category_breakdown": dict[str, float]
        }
    """
    logger.info(f"[STUB] Query spending by time period: user={user_id}, {start_date} to {end_date}")
    
    # TODO: Replace with actual database query
    
    # Mock data
    return {
        "total_amount": 4215.00,
        "transaction_count": 127,
        "start_date": start_date,
        "end_date": end_date,
        "category_breakdown": {
            "Housing": 1850.00,
            "Transportation": 450.00,
            "Food & Dining": 680.00,
            "Shopping": 320.00,
            "Utilities": 280.00,
            "Entertainment": 240.00,
            "Other": 395.00,
        }
    }


async def compare_spending_periods(
    user_id: uuid.UUID,
    period1_start: date,
    period1_end: date,
    period2_start: date,
    period2_end: date
) -> dict[str, Any]:
    """
    Compare spending between two time periods
    
    Future Implementation:
        - Query Transaction table for both periods
        - Calculate differences and percentages
        - Identify categories with biggest changes
    
    Args:
        user_id: User's UUID
        period1_start: Start of first period
        period1_end: End of first period
        period2_start: Start of second period
        period2_end: End of second period
        
    Returns:
        Dictionary with comparison data:
        {
            "period1": dict,
            "period2": dict,
            "difference": float,
            "percent_change": float,
            "category_changes": dict[str, dict]
        }
    """
    logger.info(f"[STUB] Compare spending periods: user={user_id}")
    
    # TODO: Replace with actual database query
    
    # Mock data
    return {
        "period1": {
            "total": 4215.00,
            "start_date": period1_start,
            "end_date": period1_end,
        },
        "period2": {
            "total": 3890.00,
            "start_date": period2_start,
            "end_date": period2_end,
        },
        "difference": 325.00,
        "percent_change": 8.4,
        "category_changes": {
            "Shopping": {"change": 180.00, "percent": 128.6},
            "Entertainment": {"change": 95.00, "percent": 65.5},
            "Utilities": {"change": 50.00, "percent": 21.7},
        }
    }


async def get_category_breakdown(
    user_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None
) -> dict[str, Any]:
    """
    Get spending breakdown by all categories
    
    Future Implementation:
        - Query Transaction table grouped by category
        - Calculate percentages of total
        - Order by amount descending
    
    Args:
        user_id: User's UUID
        start_date: Start of date range (optional)
        end_date: End of date range (optional)
        
    Returns:
        Dictionary with category breakdown:
        {
            "total_amount": float,
            "categories": list[dict],
            "start_date": date,
            "end_date": date
        }
    """
    logger.info(f"[STUB] Get category breakdown: user={user_id}")
    
    # TODO: Replace with actual database query
    
    # Mock data
    categories = [
        {"category": "Housing", "amount": 1850.00, "percentage": 42.0},
        {"category": "Food & Dining", "amount": 680.00, "percentage": 15.0},
        {"category": "Transportation", "amount": 450.00, "percentage": 10.0},
        {"category": "Shopping", "amount": 320.00, "percentage": 7.0},
        {"category": "Utilities", "amount": 280.00, "percentage": 6.0},
        {"category": "Entertainment", "amount": 240.00, "percentage": 5.0},
        {"category": "Other", "amount": 680.00, "percentage": 15.0},
    ]
    
    return {
        "total_amount": sum(c["amount"] for c in categories),
        "categories": categories,
        "start_date": start_date or date.today().replace(day=1),
        "end_date": end_date or date.today(),
    }


async def get_transactions(
    user_id: uuid.UUID,
    category: str | None = None,
    merchant: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    Get list of transactions with optional filters
    
    Future Implementation:
        - Query Transaction table with filters
        - Join with Account table
        - Order by date descending
        - Apply limit
    
    Args:
        user_id: User's UUID
        category: Filter by category (optional)
        merchant: Filter by merchant name (optional)
        start_date: Filter by start date (optional)
        end_date: Filter by end date (optional)
        limit: Maximum number of transactions to return
        
    Returns:
        List of transaction dictionaries
    """
    logger.info(f"[STUB] Get transactions: user={user_id}, category={category}, merchant={merchant}")
    
    # TODO: Replace with actual database query
    
    # Mock data
    return [
        {
            "id": uuid.uuid4(),
            "amount": 52.30,
            "date": date.today() - timedelta(days=1),
            "merchant": "Whole Foods",
            "category": "Groceries",
            "pending": False,
        },
        {
            "id": uuid.uuid4(),
            "amount": 18.75,
            "date": date.today() - timedelta(days=2),
            "merchant": "Starbucks",
            "category": "Dining",
            "pending": False,
        },
        {
            "id": uuid.uuid4(),
            "amount": 125.00,
            "date": date.today() - timedelta(days=3),
            "merchant": "Shell Gas Station",
            "category": "Transportation",
            "pending": False,
        },
    ][:limit]


# =============================================================================
# Utility Functions
# =============================================================================


def get_month_date_range(months_ago: int = 0) -> tuple[date, date]:
    """
    Get start and end dates for a month relative to current month
    
    Args:
        months_ago: Number of months in the past (0 = current month)
        
    Returns:
        Tuple of (start_date, end_date) for the month
    """
    today = date.today()
    
    # Calculate target month
    target_month = today.month - months_ago
    target_year = today.year
    
    while target_month < 1:
        target_month += 12
        target_year -= 1
    
    # Start of month
    start_date = date(target_year, target_month, 1)
    
    # End of month
    if target_month == 12:
        end_date = date(target_year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(target_year, target_month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def parse_time_period(period_str: str) -> tuple[date, date]:
    """
    Parse time period string to date range
    
    Args:
        period_str: Time period string like "this_month", "last_month", "this_year"
        
    Returns:
        Tuple of (start_date, end_date)
    """
    today = date.today()
    
    if period_str == "today":
        return today, today
    elif period_str == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period_str == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period_str == "last_week":
        last_week_end = today - timedelta(days=today.weekday() + 1)
        last_week_start = last_week_end - timedelta(days=6)
        return last_week_start, last_week_end
    elif period_str == "this_month":
        return get_month_date_range(0)
    elif period_str == "last_month":
        return get_month_date_range(1)
    elif period_str == "this_year":
        return date(today.year, 1, 1), today
    elif period_str == "last_year":
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    else:
        # Default to current month
        return get_month_date_range(0)

