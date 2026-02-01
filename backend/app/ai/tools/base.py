"""
Base utilities for AI tools - context management and tool registry.

This module provides:
- Context variables for passing session and user_id to tools
- Tool registry for dynamic tool loading
- Helper functions for accessing context in tools
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Callable

from sqlmodel import Session

logger = logging.getLogger(__name__)

# =============================================================================
# Context Variables
# =============================================================================
# These are set by the agent before invoking tools, allowing tools to access
# the database session and user_id without passing them as parameters

current_session: ContextVar[Session | None] = ContextVar("current_session", default=None)
current_user_id: ContextVar[uuid.UUID | None] = ContextVar("current_user_id", default=None)

# =============================================================================
# Tool Registry
# =============================================================================
# Tools register themselves on import, allowing dynamic discovery

_tool_registry: list[Callable] = []


def register_tool(tool_func: Callable) -> Callable:
    """
    Decorator to register a tool in the global registry.
    
    This allows tools to be automatically discovered and loaded by the agent.
    
    Args:
        tool_func: The tool function to register
        
    Returns:
        The same tool function (decorator pattern)
        
    Example:
        @tool
        @register_tool
        def my_tool(param: str) -> dict:
            pass
    """
    if tool_func not in _tool_registry:
        _tool_registry.append(tool_func)
        logger.debug(f"Registered tool: {tool_func.name if hasattr(tool_func, 'name') else tool_func.__name__}")
    return tool_func


def get_all_tools() -> list[Callable]:
    """
    Return all registered tools.
    
    Returns:
        List of all registered tool functions
    """
    logger.info(f"Retrieved {len(_tool_registry)} registered tools")
    return _tool_registry.copy()


# =============================================================================
# Context Access Helpers
# =============================================================================


def get_session() -> Session:
    """
    Get the current database session from context.
    
    Returns:
        The database session for the current request
        
    Raises:
        RuntimeError: If session is not set in context
    """
    session = current_session.get()
    if session is None:
        raise RuntimeError(
            "Database session not set in context. "
            "Ensure current_session.set() is called before invoking tools."
        )
    return session


def get_user_id() -> uuid.UUID:
    """
    Get the current user ID from context.
    
    Returns:
        The UUID of the authenticated user
        
    Raises:
        RuntimeError: If user_id is not set in context
    """
    user_id = current_user_id.get()
    if user_id is None:
        raise RuntimeError(
            "User ID not set in context. "
            "Ensure current_user_id.set() is called before invoking tools."
        )
    return user_id


def set_context(session: Session, user_id: uuid.UUID) -> None:
    """
    Set the session and user_id in context for tool execution.
    
    This should be called by the agent before invoking any tools.
    
    Args:
        session: Database session
        user_id: Authenticated user's UUID
        
    Example:
        set_context(db_session, user.id)
        # Now tools can be invoked
    """
    current_session.set(session)
    current_user_id.set(user_id)
    logger.debug(f"Context set: user_id={user_id}")


def clear_context() -> None:
    """
    Clear the context variables.
    
    This should be called after tool execution is complete to prevent
    context leakage between requests.
    """
    current_session.set(None)
    current_user_id.set(None)
    logger.debug("Context cleared")
