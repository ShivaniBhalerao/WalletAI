"""
Tool definitions for Financial Analyst Agent

This module defines tools that the agent can use to query and analyze financial data
from the database.
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlmodel import Session, func, select

from app.models import Account, Transaction

logger = logging.getLogger(__name__)


# =============================================================================
# Database Query Tools
# =============================================================================


def query_spending_by_category(
    session: Session,
    user_id: uuid.UUID,
    category: str,
    start_date: date | None = None,
    end_date: date | None = None
) -> dict[str, Any]:
    """
    Query user's spending in a specific category for a given time period
    
    Args:
        session: Database session
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
    logger.info(f"Query spending by category: user={user_id}, category={category}")
    
    # Set default date range if not provided
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    
    try:
        # Query total spending and transaction count
        total_query = (
            select(
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count")
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.category.ilike(f"%{category}%"))
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
        )
        
        result = session.exec(total_query).first()
        total_amount = float(result.total) if result and result.total else 0.0
        transaction_count = int(result.count) if result and result.count else 0
        
        # Query top merchants
        merchant_query = (
            select(
                Transaction.merchant_name,
                func.sum(Transaction.amount).label("merchant_total")
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.category.ilike(f"%{category}%"))
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
            .group_by(Transaction.merchant_name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(3)
        )
        
        merchant_results = session.exec(merchant_query).all()
        top_merchants = [
            {"name": row.merchant_name, "amount": float(row.merchant_total)}
            for row in merchant_results
        ]
        
        logger.info(f"Query result: total=${total_amount:.2f}, {transaction_count} transactions")
        
        return {
            "category": category,
            "total_amount": total_amount,
            "transaction_count": transaction_count,
            "start_date": start_date,
            "end_date": end_date,
            "top_merchants": top_merchants
        }
        
    except Exception as e:
        logger.error(f"Error querying spending by category: {e}", exc_info=True)
        # Return empty result on error
        return {
            "category": category,
            "total_amount": 0.0,
            "transaction_count": 0,
            "start_date": start_date,
            "end_date": end_date,
            "top_merchants": []
        }


def query_spending_by_time_period(
    session: Session,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date
) -> dict[str, Any]:
    """
    Query total spending for a time period with category breakdown
    
    Args:
        session: Database session
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
    logger.info(f"Query spending by time period: user={user_id}, {start_date} to {end_date}")
    
    try:
        # Query total spending and transaction count
        total_query = (
            select(
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count")
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
        )
        
        result = session.exec(total_query).first()
        total_amount = float(result.total) if result and result.total else 0.0
        transaction_count = int(result.count) if result and result.count else 0
        
        # Query category breakdown
        category_query = (
            select(
                Transaction.category,
                func.sum(Transaction.amount).label("category_total")
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.auth_date >= start_date)
            .where(Transaction.auth_date <= end_date)
            .where(Transaction.pending == False)
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
        )
        
        category_results = session.exec(category_query).all()
        category_breakdown = {
            row.category: float(row.category_total)
            for row in category_results
        }
        
        logger.info(f"Query result: total=${total_amount:.2f}, {transaction_count} transactions, {len(category_breakdown)} categories")
        
        return {
            "total_amount": total_amount,
            "transaction_count": transaction_count,
            "start_date": start_date,
            "end_date": end_date,
            "category_breakdown": category_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error querying spending by time period: {e}", exc_info=True)
        return {
            "total_amount": 0.0,
            "transaction_count": 0,
            "start_date": start_date,
            "end_date": end_date,
            "category_breakdown": {}
        }


def compare_spending_periods(
    session: Session,
    user_id: uuid.UUID,
    period1_start: date,
    period1_end: date,
    period2_start: date,
    period2_end: date
) -> dict[str, Any]:
    """
    Compare spending between two time periods
    
    Args:
        session: Database session
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
    logger.info(f"Compare spending periods: user={user_id}")
    
    try:
        # Get data for both periods
        period1_data = query_spending_by_time_period(session, user_id, period1_start, period1_end)
        period2_data = query_spending_by_time_period(session, user_id, period2_start, period2_end)
        
        # Calculate difference and percent change
        difference = period1_data["total_amount"] - period2_data["total_amount"]
        
        if period2_data["total_amount"] > 0:
            percent_change = (difference / period2_data["total_amount"]) * 100
        else:
            percent_change = 0.0
        
        # Calculate category-level changes
        category_changes = {}
        period1_categories = period1_data["category_breakdown"]
        period2_categories = period2_data["category_breakdown"]
        
        # Get all unique categories from both periods
        all_categories = set(period1_categories.keys()) | set(period2_categories.keys())
        
        for category in all_categories:
            amount1 = period1_categories.get(category, 0.0)
            amount2 = period2_categories.get(category, 0.0)
            change = amount1 - amount2
            
            if amount2 > 0:
                percent = (change / amount2) * 100
            else:
                percent = 0.0 if change == 0 else 100.0
            
            # Only include categories with significant changes
            if abs(change) > 0.01:
                category_changes[category] = {
                    "change": change,
                    "percent": percent
                }
        
        # Sort by absolute change and take top 5
        sorted_changes = dict(
            sorted(category_changes.items(), key=lambda x: abs(x[1]["change"]), reverse=True)[:5]
        )
        
        logger.info(f"Comparison result: difference=${difference:.2f}, percent_change={percent_change:.1f}%")
        
        return {
            "period1": {
                "total": period1_data["total_amount"],
                "start_date": period1_start,
                "end_date": period1_end,
            },
            "period2": {
                "total": period2_data["total_amount"],
                "start_date": period2_start,
                "end_date": period2_end,
            },
            "difference": difference,
            "percent_change": percent_change,
            "category_changes": sorted_changes
        }
        
    except Exception as e:
        logger.error(f"Error comparing spending periods: {e}", exc_info=True)
        return {
            "period1": {
                "total": 0.0,
                "start_date": period1_start,
                "end_date": period1_end,
            },
            "period2": {
                "total": 0.0,
                "start_date": period2_start,
                "end_date": period2_end,
            },
            "difference": 0.0,
            "percent_change": 0.0,
            "category_changes": {}
        }


def get_category_breakdown(
    session: Session,
    user_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None
) -> dict[str, Any]:
    """
    Get spending breakdown by all categories with percentages
    
    Args:
        session: Database session
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
    logger.info(f"Get category breakdown: user={user_id}")
    
    # Set default date range if not provided
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    
    try:
        # Get spending by time period (includes category breakdown)
        data = query_spending_by_time_period(session, user_id, start_date, end_date)
        
        total_amount = data["total_amount"]
        category_breakdown = data["category_breakdown"]
        
        # Convert to list with percentages
        categories = []
        for category, amount in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total_amount * 100) if total_amount > 0 else 0.0
            categories.append({
                "category": category,
                "amount": amount,
                "percentage": round(percentage, 1)
            })
        
        logger.info(f"Category breakdown: {len(categories)} categories, total=${total_amount:.2f}")
        
        return {
            "total_amount": total_amount,
            "categories": categories,
            "start_date": start_date,
            "end_date": end_date,
        }
        
    except Exception as e:
        logger.error(f"Error getting category breakdown: {e}", exc_info=True)
        return {
            "total_amount": 0.0,
            "categories": [],
            "start_date": start_date,
            "end_date": end_date,
        }


def get_transactions(
    session: Session,
    user_id: uuid.UUID,
    category: str | None = None,
    merchant: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    Get list of transactions with optional filters
    
    Args:
        session: Database session
        user_id: User's UUID
        category: Filter by category (optional)
        merchant: Filter by merchant name (optional)
        start_date: Filter by start date (optional)
        end_date: Filter by end date (optional)
        limit: Maximum number of transactions to return
        
    Returns:
        List of transaction dictionaries
    """
    logger.info(f"Get transactions: user={user_id}, category={category}, merchant={merchant}")
    
    try:
        # Build query
        query = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .where(Transaction.pending == False)
        )
        
        # Apply filters
        if category:
            query = query.where(Transaction.category.ilike(f"%{category}%"))
        
        if merchant:
            query = query.where(Transaction.merchant_name.ilike(f"%{merchant}%"))
        
        if start_date:
            query = query.where(Transaction.auth_date >= start_date)
        
        if end_date:
            query = query.where(Transaction.auth_date <= end_date)
        
        # Order by date descending and apply limit
        query = query.order_by(Transaction.auth_date.desc()).limit(limit)
        
        # Execute query
        results = session.exec(query).all()
        
        # Convert to dictionaries
        transactions = [
            {
                "id": str(txn.id),
                "amount": float(txn.amount),
                "date": txn.auth_date,
                "merchant": txn.merchant_name,
                "category": txn.category,
                "pending": txn.pending,
            }
            for txn in results
        ]
        
        logger.info(f"Retrieved {len(transactions)} transactions")
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error getting transactions: {e}", exc_info=True)
        return []


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
