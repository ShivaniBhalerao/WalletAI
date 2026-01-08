"""
SyncOrchestrator - Orchestrates the complete Plaid sync workflow.

This orchestrator coordinates between PlaidService and DatabaseService to:
- Handle Plaid Link token creation
- Exchange public tokens for access tokens
- Sync accounts and transactions for users
- Manage cursor-based incremental syncs
"""

import logging
import uuid
from typing import Any

from sqlmodel import Session

from app.core.db_service import DatabaseService, DatabaseServiceError
from app.core.plaid_service import PlaidService, PlaidServiceError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyncOrchestratorError(Exception):
    """Base exception for sync orchestrator errors."""
    
    def __init__(self, message: str, error_code: str | None = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class SyncOrchestrator:
    """
    Orchestrator for coordinating Plaid and Database services.
    
    This class provides high-level methods for:
    - Creating Plaid Link tokens for frontend
    - Exchanging public tokens and storing access tokens
    - Syncing all transactions for a user
    - Syncing individual Plaid items with cursor-based pagination
    
    The orchestrator handles the complete workflow from Plaid API calls
    to database persistence.
    """
    
    def __init__(
        self,
        session: Session,
        plaid_service: PlaidService | None = None,
    ) -> None:
        """
        Initialize the SyncOrchestrator.
        
        Args:
            session: SQLModel database session
            plaid_service: Optional PlaidService instance (creates new one if None)
        """
        self.db_service = DatabaseService(session)
        self.plaid_service = plaid_service or PlaidService()
        logger.info("SyncOrchestrator initialized")
    
    def handle_link_token_request(
        self,
        user_id: uuid.UUID,
        client_name: str = "WalletAI",
    ) -> dict[str, Any]:
        """
        Create a Plaid Link token for frontend initialization.
        
        This is the first step in the Plaid Link flow. The returned link token
        is used by the frontend to initialize Plaid Link.
        
        Args:
            user_id: ID of the user requesting the link token
            client_name: Name to display in Plaid Link (default: "WalletAI")
            
        Returns:
            Dictionary containing:
                - link_token: Token to be used in Plaid Link
                - expiration: When the link token expires
                - request_id: Plaid request ID for tracking
                
        Raises:
            SyncOrchestratorError: If link token creation fails
            
        Example:
            >>> orchestrator = SyncOrchestrator(session)
            >>> result = orchestrator.handle_link_token_request(user_id)
            >>> link_token = result["link_token"]
        """
        try:
            logger.info(f"Handling link token request for user_id: {user_id}")
            
            result = self.plaid_service.create_link_token(
                user_id=str(user_id),
                client_name=client_name,
            )
            
            logger.info(
                f"Link token created successfully for user_id: {user_id}"
            )
            
            return result
            
        except PlaidServiceError as e:
            error_msg = f"Failed to create link token: {e.message}"
            logger.error(error_msg)
            raise SyncOrchestratorError(
                message=error_msg,
                error_code=getattr(e, "error_code", None)
            )
        except Exception as e:
            error_msg = f"Unexpected error creating link token: {e}"
            logger.error(error_msg, exc_info=True)
            raise SyncOrchestratorError(message=error_msg)
    
    def handle_public_token_exchange(
        self,
        user_id: uuid.UUID,
        public_token: str,
        institution_name: str,
    ) -> dict[str, Any]:
        """
        Complete Plaid Link flow by exchanging public token for access token.
        
        This is the second step after the user completes Plaid Link. The public
        token is exchanged for an access token, which is then stored in the database
        along with initial account data.
        
        Args:
            user_id: ID of the user
            public_token: Public token received from Plaid Link
            institution_name: Name of the financial institution
            
        Returns:
            Dictionary containing:
                - plaid_item: Created PlaidItem instance
                - accounts: List of created Account instances
                - item_id: Plaid item identifier
                
        Raises:
            SyncOrchestratorError: If exchange or database operations fail
            
        Example:
            >>> orchestrator = SyncOrchestrator(session)
            >>> result = orchestrator.handle_public_token_exchange(
            ...     user_id=user_id,
            ...     public_token="public-sandbox-xxx",
            ...     institution_name="Chase Bank"
            ... )
            >>> plaid_item = result["plaid_item"]
            >>> accounts = result["accounts"]
        """
        try:
            logger.info(
                f"Handling public token exchange for user_id: {user_id}, "
                f"institution: {institution_name}"
            )
            
            # Exchange public token for access token
            exchange_result = self.plaid_service.exchange_public_token(
                public_token=public_token
            )
            
            access_token = exchange_result["access_token"]
            item_id = exchange_result["item_id"]
            
            logger.info(f"Public token exchanged, item_id: {item_id}")
            
            # Create PlaidItem in database
            plaid_item = self.db_service.create_plaid_item(
                user_id=user_id,
                item_id=item_id,
                access_token=access_token,
                institution_name=institution_name,
            )
            
            # Fetch and store accounts
            accounts_result = self.plaid_service.get_accounts(
                access_token=access_token
            )
            
            accounts = self.db_service.upsert_accounts(
                accounts=accounts_result["accounts"],
                plaid_item_id=plaid_item.id,
                user_id=user_id,
            )
            
            logger.info(
                f"Public token exchange complete, "
                f"plaid_item_id: {plaid_item.id}, "
                f"accounts: {len(accounts)}"
            )
            
            return {
                "plaid_item": plaid_item,
                "accounts": accounts,
                "item_id": item_id,
            }
            
        except PlaidServiceError as e:
            error_msg = f"Plaid API error during token exchange: {e.message}"
            logger.error(error_msg)
            raise SyncOrchestratorError(
                message=error_msg,
                error_code=getattr(e, "error_code", None)
            )
        except DatabaseServiceError as e:
            error_msg = f"Database error during token exchange: {e.message}"
            logger.error(error_msg)
            raise SyncOrchestratorError(message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during token exchange: {e}"
            logger.error(error_msg, exc_info=True)
            raise SyncOrchestratorError(message=error_msg)
    
    def sync_user_transactions(
        self,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Sync all transactions for a user across all their Plaid items.
        
        This method retrieves all PlaidItems for the user and syncs transactions
        for each one using cursor-based pagination.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing:
                - total_added: Total number of transactions added
                - total_modified: Total number of transactions modified
                - total_removed: Total number of transactions removed
                - items_synced: Number of PlaidItems synced
                - results: List of sync results per PlaidItem
                
        Raises:
            SyncOrchestratorError: If sync fails
            
        Example:
            >>> orchestrator = SyncOrchestrator(session)
            >>> result = orchestrator.sync_user_transactions(user_id)
            >>> print(f"Added: {result['total_added']}, "
            ...       f"Modified: {result['total_modified']}, "
            ...       f"Removed: {result['total_removed']}")
        """
        try:
            logger.info(f"Syncing transactions for user_id: {user_id}")
            
            # Get all PlaidItems for the user
            plaid_items = self.db_service.get_plaid_items_for_user(user_id)
            
            if not plaid_items:
                logger.info(f"No PlaidItems found for user_id: {user_id}")
                return {
                    "total_added": 0,
                    "total_modified": 0,
                    "total_removed": 0,
                    "items_synced": 0,
                    "results": [],
                }
            
            logger.info(
                f"Found {len(plaid_items)} PlaidItems for user_id: {user_id}"
            )
            
            # Sync each PlaidItem
            total_added = 0
            total_modified = 0
            total_removed = 0
            results = []
            
            for plaid_item in plaid_items:
                try:
                    result = self.sync_plaid_item(plaid_item)
                    total_added += result["added_count"]
                    total_modified += result["modified_count"]
                    total_removed += result["removed_count"]
                    results.append(result)
                except Exception as e:
                    logger.error(
                        f"Error syncing plaid_item_id {plaid_item.id}: {e}",
                        exc_info=True
                    )
                    results.append({
                        "plaid_item_id": plaid_item.id,
                        "institution_name": plaid_item.institution_name,
                        "success": False,
                        "error": str(e),
                    })
            
            logger.info(
                f"User transaction sync complete for user_id: {user_id}, "
                f"added: {total_added}, modified: {total_modified}, "
                f"removed: {total_removed}"
            )
            
            return {
                "total_added": total_added,
                "total_modified": total_modified,
                "total_removed": total_removed,
                "items_synced": len(plaid_items),
                "results": results,
            }
            
        except DatabaseServiceError as e:
            error_msg = f"Database error syncing user transactions: {e.message}"
            logger.error(error_msg)
            raise SyncOrchestratorError(message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error syncing user transactions: {e}"
            logger.error(error_msg, exc_info=True)
            raise SyncOrchestratorError(message=error_msg)
    
    def sync_plaid_item(
        self,
        plaid_item: Any,
    ) -> dict[str, Any]:
        """
        Sync transactions for a single PlaidItem.
        
        This method performs cursor-based transaction sync for a PlaidItem:
        1. Calls Plaid Transactions Sync API with current cursor
        2. Upserts accounts (in case of updates)
        3. Maps Plaid account IDs to database Account IDs
        4. Upserts transactions
        5. Handles removed transactions
        6. Updates sync cursor
        
        Args:
            plaid_item: PlaidItem instance to sync
            
        Returns:
            Dictionary containing:
                - plaid_item_id: ID of the PlaidItem
                - institution_name: Name of the institution
                - added_count: Number of transactions added
                - modified_count: Number of transactions modified
                - removed_count: Number of transactions removed
                - success: Whether sync was successful
                
        Raises:
            SyncOrchestratorError: If sync fails
            
        Example:
            >>> orchestrator = SyncOrchestrator(session)
            >>> plaid_item = db_service.get_plaid_item_by_id(plaid_item_id)
            >>> result = orchestrator.sync_plaid_item(plaid_item)
            >>> print(f"Added {result['added_count']} transactions")
        """
        try:
            logger.info(
                f"Syncing plaid_item_id: {plaid_item.id}, "
                f"institution: {plaid_item.institution_name}"
            )
            
            # Get the current cursor
            cursor = plaid_item.cursor
            
            # Sync all transactions with pagination
            sync_result = self.plaid_service.sync_all_transactions(
                access_token=plaid_item.access_token,
                cursor=cursor,
            )
            
            added = sync_result["added"]
            modified = sync_result["modified"]
            removed = sync_result["removed"]
            next_cursor = sync_result["next_cursor"]
            
            logger.info(
                f"Plaid sync complete for item {plaid_item.id}: "
                f"added={len(added)}, modified={len(modified)}, "
                f"removed={len(removed)}"
            )
            
            # Get all accounts for this PlaidItem
            # We need to refresh accounts in case they changed
            accounts_result = self.plaid_service.get_accounts(
                access_token=plaid_item.access_token
            )
            
            # Upsert accounts
            accounts = self.db_service.upsert_accounts(
                accounts=accounts_result["accounts"],
                plaid_item_id=plaid_item.id,
                user_id=plaid_item.user_id,
            )
            
            # Create mapping from plaid_account_id to Account.id
            account_mapping = {
                account.plaid_account_id: account.id
                for account in accounts
                if account.plaid_account_id
            }
            
            # Upsert added and modified transactions
            all_transactions = added + modified
            
            if all_transactions:
                self.db_service.upsert_transactions(
                    transactions=all_transactions,
                    account_mapping=account_mapping,
                )
            
            # Handle removed transactions
            removed_count = 0
            if removed:
                removed_ids = [
                    txn.get("transaction_id")
                    for txn in removed
                    if txn.get("transaction_id")
                ]
                
                if removed_ids:
                    removed_count = self.db_service.delete_transactions(
                        transaction_ids=removed_ids
                    )
            
            # Update sync cursor
            self.db_service.update_sync_cursor(
                plaid_item_id=plaid_item.id,
                cursor=next_cursor,
            )
            
            logger.info(
                f"PlaidItem sync complete for plaid_item_id: {plaid_item.id}"
            )
            
            return {
                "plaid_item_id": str(plaid_item.id),
                "institution_name": plaid_item.institution_name,
                "added_count": len(added),
                "modified_count": len(modified),
                "removed_count": removed_count,
                "success": True,
            }
            
        except PlaidServiceError as e:
            error_msg = (
                f"Plaid API error syncing item {plaid_item.id}: {e.message}"
            )
            logger.error(error_msg)
            raise SyncOrchestratorError(
                message=error_msg,
                error_code=getattr(e, "error_code", None)
            )
        except DatabaseServiceError as e:
            error_msg = (
                f"Database error syncing item {plaid_item.id}: {e.message}"
            )
            logger.error(error_msg)
            raise SyncOrchestratorError(message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error syncing item {plaid_item.id}: {e}"
            logger.error(error_msg, exc_info=True)
            raise SyncOrchestratorError(message=error_msg)
