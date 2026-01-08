"""
Plaid API Routes

This module provides endpoints for integrating with Plaid Link and syncing
financial data from connected bank accounts.

Endpoints:
- GET /plaid/link-token: Generate a Plaid Link token for frontend initialization
- POST /plaid/exchange-token: Exchange public token for access token
- POST /plaid/sync: Sync transactions for all connected accounts
- GET /plaid/status: Check if user has connected Plaid accounts
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.core.sync_orchestrator import SyncOrchestrator, SyncOrchestratorError
from app.models import (
    Message,
    PlaidExchangeRequest,
    PlaidItemPublic,
    PlaidLinkTokenResponse,
    PlaidStatusResponse,
    PlaidSyncResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plaid", tags=["plaid"])


@router.get("/link-token", response_model=PlaidLinkTokenResponse)
def get_link_token(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Generate a Plaid Link token for frontend initialization.
    
    This endpoint creates a link token that the frontend uses to initialize
    Plaid Link, allowing users to connect their bank accounts.
    
    Returns:
        PlaidLinkTokenResponse containing the link token and expiration time
        
    Raises:
        HTTPException: If link token creation fails
        
    Example:
        GET /api/v1/plaid/link-token
        Response: {
            "link_token": "link-sandbox-xxx",
            "expiration": "2024-01-01T12:00:00Z"
        }
    """
    try:
        logger.info(f"Creating Plaid link token for user: {current_user.id}")
        
        orchestrator = SyncOrchestrator(session)
        result = orchestrator.handle_link_token_request(
            user_id=current_user.id,
            client_name="WalletAI"
        )
        
        logger.info(
            f"Link token created successfully for user: {current_user.id}"
        )
        
        return PlaidLinkTokenResponse(
            link_token=result["link_token"],
            expiration=result["expiration"]
        )
        
    except SyncOrchestratorError as e:
        logger.error(
            f"Failed to create link token for user {current_user.id}: {e.message}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Plaid link token: {e.message}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error creating link token for user {current_user.id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating link token"
        )


@router.post("/exchange-token", response_model=Message)
def exchange_public_token(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: PlaidExchangeRequest,
) -> Any:
    """
    Exchange a Plaid public token for an access token.
    
    This endpoint is called after the user completes Plaid Link. It exchanges
    the public token for an access token, stores it in the database, and
    fetches initial account data.
    
    Args:
        request: PlaidExchangeRequest containing public_token and institution_name
        
    Returns:
        Message confirming successful token exchange
        
    Raises:
        HTTPException: If token exchange fails
        
    Example:
        POST /api/v1/plaid/exchange-token
        Body: {
            "public_token": "public-sandbox-xxx",
            "institution_name": "Chase Bank"
        }
        Response: {
            "message": "Bank account connected successfully"
        }
    """
    try:
        logger.info(
            f"Exchanging public token for user: {current_user.id}, "
            f"institution: {request.institution_name}"
        )
        
        orchestrator = SyncOrchestrator(session)
        result = orchestrator.handle_public_token_exchange(
            user_id=current_user.id,
            public_token=request.public_token,
            institution_name=request.institution_name,
        )
        
        plaid_item = result["plaid_item"]
        accounts = result["accounts"]
        
        logger.info(
            f"Public token exchanged successfully for user: {current_user.id}, "
            f"plaid_item_id: {plaid_item.id}, accounts: {len(accounts)}"
        )
        
        return Message(
            message=f"Bank account connected successfully. {len(accounts)} "
                    f"account(s) found."
        )
        
    except SyncOrchestratorError as e:
        logger.error(
            f"Failed to exchange public token for user {current_user.id}: {e.message}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange token: {e.message}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error exchanging token for user {current_user.id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while exchanging token"
        )


@router.post("/sync", response_model=PlaidSyncResponse)
def sync_transactions(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Sync transactions for all connected Plaid accounts.
    
    This endpoint triggers a sync of transactions across all bank accounts
    connected via Plaid for the current user. It uses cursor-based pagination
    to efficiently fetch only new and updated transactions.
    
    Returns:
        PlaidSyncResponse with counts of added, modified, and removed transactions
        
    Raises:
        HTTPException: If sync fails or no accounts are connected
        
    Example:
        POST /api/v1/plaid/sync
        Response: {
            "total_added": 15,
            "total_modified": 3,
            "total_removed": 1,
            "items_synced": 2
        }
    """
    try:
        logger.info(f"Syncing transactions for user: {current_user.id}")
        
        orchestrator = SyncOrchestrator(session)
        result = orchestrator.sync_user_transactions(user_id=current_user.id)
        
        if result["items_synced"] == 0:
            logger.warning(
                f"No Plaid items found for user: {current_user.id}"
            )
            raise HTTPException(
                status_code=404,
                detail="No connected bank accounts found. Please connect a bank account first."
            )
        
        logger.info(
            f"Transactions synced successfully for user: {current_user.id}, "
            f"added: {result['total_added']}, "
            f"modified: {result['total_modified']}, "
            f"removed: {result['total_removed']}, "
            f"items_synced: {result['items_synced']}"
        )
        
        return PlaidSyncResponse(
            total_added=result["total_added"],
            total_modified=result["total_modified"],
            total_removed=result["total_removed"],
            items_synced=result["items_synced"],
        )
        
    except SyncOrchestratorError as e:
        logger.error(
            f"Failed to sync transactions for user {current_user.id}: {e.message}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync transactions: {e.message}"
        )
    except HTTPException:
        # Re-raise HTTPException without wrapping
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error syncing transactions for user {current_user.id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while syncing transactions"
        )


@router.get("/status", response_model=PlaidStatusResponse)
def get_plaid_status(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Check if user has connected Plaid accounts.
    
    This endpoint returns the connection status and a list of connected
    PlaidItems for the current user.
    
    Returns:
        PlaidStatusResponse with connection status and list of PlaidItems
        
    Raises:
        HTTPException: If status check fails
        
    Example:
        GET /api/v1/plaid/status
        Response: {
            "is_connected": true,
            "items": [
                {
                    "id": "...",
                    "user_id": "...",
                    "item_id": "...",
                    "institution_name": "Chase Bank",
                    "cursor": "..."
                }
            ]
        }
    """
    try:
        logger.info(f"Checking Plaid status for user: {current_user.id}")
        
        orchestrator = SyncOrchestrator(session)
        plaid_items = orchestrator.db_service.get_plaid_items_for_user(
            user_id=current_user.id
        )
        
        is_connected = len(plaid_items) > 0
        
        # Convert PlaidItem objects to PlaidItemPublic
        items_public = [
            PlaidItemPublic(
                id=item.id,
                user_id=item.user_id,
                item_id=item.item_id,
                institution_name=item.institution_name,
                cursor=item.cursor,
            )
            for item in plaid_items
        ]
        
        logger.info(
            f"Plaid status retrieved for user: {current_user.id}, "
            f"is_connected: {is_connected}, items: {len(items_public)}"
        )
        
        return PlaidStatusResponse(
            is_connected=is_connected,
            items=items_public
        )
        
    except Exception as e:
        logger.error(
            f"Unexpected error checking Plaid status for user {current_user.id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while checking Plaid status"
        )
