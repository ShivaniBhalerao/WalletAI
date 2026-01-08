"""
PlaidService - Core service for Plaid API interactions.

This service handles all communication with the Plaid API including:
- Creating link tokens for Plaid Link flow
- Exchanging public tokens for access tokens
- Fetching account information
- Syncing transactions using the Transactions Sync API
"""

import logging
from datetime import datetime
from typing import Any

from plaid import ApiException
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlaidServiceError(Exception):
    """Base exception for Plaid service errors."""
    
    def __init__(self, message: str, error_code: str | None = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class PlaidAPIError(PlaidServiceError):
    """Exception raised for Plaid API errors."""
    pass


class PlaidService:
    """
    Service class for interacting with the Plaid API.
    
    This service provides methods for:
    - Creating link tokens for frontend Plaid Link initialization
    - Exchanging public tokens for access tokens
    - Fetching account information
    - Syncing transactions with cursor-based pagination
    
    All methods include comprehensive error handling and logging.
    """
    
    def __init__(self) -> None:
        """
        Initialize the PlaidService with configuration from settings.
        
        Sets up the Plaid API client with appropriate credentials and environment.
        """
        import plaid
        
        # Map environment string to Plaid environment
        env_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Sandbox,  # Use Sandbox for development
            "production": plaid.Environment.Production,
        }
        
        configuration = plaid.Configuration(
            host=env_map[settings.PLAID_ENV],
            api_key={
                "clientId": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
        
        logger.info(
            f"PlaidService initialized with environment: {settings.PLAID_ENV}"
        )
    
    def create_link_token(
        self,
        user_id: str,
        client_name: str = "WalletAI",
    ) -> dict[str, Any]:
        """
        Create a link token for Plaid Link initialization.
        
        The link token is used by the frontend to initialize Plaid Link,
        which allows users to connect their bank accounts.
        
        Args:
            user_id: Unique identifier for the user
            client_name: Name to display in Plaid Link (default: "WalletAI")
            
        Returns:
            Dictionary containing:
                - link_token: Token to be used in Plaid Link
                - expiration: When the link token expires
                - request_id: Plaid request ID for tracking
                
        Raises:
            PlaidAPIError: If the Plaid API returns an error
            PlaidServiceError: For other service-level errors
            
        Example:
            >>> service = PlaidService()
            >>> result = service.create_link_token("user-123")
            >>> link_token = result["link_token"]
        """
        try:
            logger.info(f"Creating link token for user_id: {user_id}")
            
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                client_name=client_name,
                products=[Products("transactions"), Products("auth")],
                country_codes=[CountryCode("US")],
                language="en",
            )
            
            response = self.client.link_token_create(request)
            result = response.to_dict()
            
            logger.info(
                f"Link token created successfully for user_id: {user_id}, "
                f"request_id: {result.get('request_id')}"
            )
            
            return {
                "link_token": result["link_token"],
                "expiration": result["expiration"],
                "request_id": result["request_id"],
            }
            
        except ApiException as e:
            error_msg = f"Plaid API error creating link token: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidAPIError(
                message=error_msg,
                error_code=getattr(e, "error_code", None)
            )
        except Exception as e:
            error_msg = f"Unexpected error creating link token: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidServiceError(message=error_msg)
    
    def exchange_public_token(self, public_token: str) -> dict[str, Any]:
        """
        Exchange a public token for an access token.
        
        After a user completes the Plaid Link flow, the frontend receives
        a public token. This method exchanges that public token for an
        access token that can be used for subsequent API calls.
        
        Args:
            public_token: Public token received from Plaid Link
            
        Returns:
            Dictionary containing:
                - access_token: Long-lived access token for API calls
                - item_id: Unique identifier for this Plaid Item
                - request_id: Plaid request ID for tracking
                
        Raises:
            PlaidAPIError: If the Plaid API returns an error
            PlaidServiceError: For other service-level errors
            
        Example:
            >>> service = PlaidService()
            >>> result = service.exchange_public_token("public-sandbox-xxx")
            >>> access_token = result["access_token"]
            >>> item_id = result["item_id"]
        """
        try:
            logger.info("Exchanging public token for access token")
            
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            result = response.to_dict()
            
            logger.info(
                f"Public token exchanged successfully, "
                f"item_id: {result['item_id']}, "
                f"request_id: {result.get('request_id')}"
            )
            
            return {
                "access_token": result["access_token"],
                "item_id": result["item_id"],
                "request_id": result.get("request_id"),
            }
            
        except ApiException as e:
            error_msg = f"Plaid API error exchanging public token: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidAPIError(
                message=error_msg,
                error_code=getattr(e, "error_code", None)
            )
        except Exception as e:
            error_msg = f"Unexpected error exchanging public token: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidServiceError(message=error_msg)
    
    def get_accounts(self, access_token: str) -> dict[str, Any]:
        """
        Fetch account information for a Plaid Item.
        
        Retrieves all accounts associated with the given access token,
        including account names, types, balances, and other metadata.
        
        Args:
            access_token: Access token for the Plaid Item
            
        Returns:
            Dictionary containing:
                - accounts: List of account dictionaries with fields:
                    - account_id: Plaid account identifier
                    - name: Account name
                    - official_name: Official account name from institution
                    - type: Account type (e.g., "depository", "credit")
                    - subtype: Account subtype (e.g., "checking", "savings")
                    - balances: Current balance information
                - item: Item metadata
                - request_id: Plaid request ID for tracking
                
        Raises:
            PlaidAPIError: If the Plaid API returns an error
            PlaidServiceError: For other service-level errors
            
        Example:
            >>> service = PlaidService()
            >>> result = service.get_accounts("access-sandbox-xxx")
            >>> for account in result["accounts"]:
            ...     print(f"{account['name']}: ${account['balances']['current']}")
        """
        try:
            logger.info("Fetching accounts from Plaid")
            
            from plaid.model.accounts_get_request import AccountsGetRequest
            
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            result = response.to_dict()
            
            logger.info(
                f"Accounts fetched successfully, "
                f"count: {len(result['accounts'])}, "
                f"request_id: {result.get('request_id')}"
            )
            
            return {
                "accounts": result["accounts"],
                "item": result.get("item"),
                "request_id": result.get("request_id"),
            }
            
        except ApiException as e:
            error_msg = f"Plaid API error fetching accounts: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidAPIError(
                message=error_msg,
                error_code=getattr(e, "error_code", None)
            )
        except Exception as e:
            error_msg = f"Unexpected error fetching accounts: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidServiceError(message=error_msg)
    
    def sync_transactions(
        self,
        access_token: str,
        cursor: str | None = None,
        count: int = 500,
    ) -> dict[str, Any]:
        """
        Sync transactions using Plaid's Transactions Sync API.
        
        This method implements cursor-based pagination to efficiently sync
        transactions. It returns new, modified, and removed transactions
        since the last sync.
        
        Args:
            access_token: Access token for the Plaid Item
            cursor: Optional cursor from previous sync for incremental updates
            count: Maximum number of transactions to fetch (default: 500)
            
        Returns:
            Dictionary containing:
                - added: List of newly added transactions
                - modified: List of modified transactions
                - removed: List of removed transaction objects with:
                    - transaction_id: ID of removed transaction
                - next_cursor: Cursor for the next sync call
                - has_more: Whether more data is available
                - request_id: Plaid request ID for tracking
                
        Raises:
            PlaidAPIError: If the Plaid API returns an error
            PlaidServiceError: For other service-level errors
            
        Example:
            >>> service = PlaidService()
            >>> # Initial sync
            >>> result = service.sync_transactions("access-sandbox-xxx")
            >>> cursor = result["next_cursor"]
            >>> # Subsequent sync
            >>> result = service.sync_transactions("access-sandbox-xxx", cursor)
            
        Note:
            The cursor should be stored and used for subsequent syncs to
            avoid re-fetching all historical data.
        """
        try:
            logger.info(
                f"Syncing transactions, cursor: {cursor[:20] if cursor else 'None'}..."
            )
            
            request_data = {
                "access_token": access_token,
                "count": count,
            }
            
            if cursor:
                request_data["cursor"] = cursor
            
            request = TransactionsSyncRequest(**request_data)
            response = self.client.transactions_sync(request)
            result = response.to_dict()
            
            logger.info(
                f"Transactions synced successfully, "
                f"added: {len(result.get('added', []))}, "
                f"modified: {len(result.get('modified', []))}, "
                f"removed: {len(result.get('removed', []))}, "
                f"has_more: {result.get('has_more', False)}, "
                f"request_id: {result.get('request_id')}"
            )
            
            return {
                "added": result.get("added", []),
                "modified": result.get("modified", []),
                "removed": result.get("removed", []),
                "next_cursor": result.get("next_cursor"),
                "has_more": result.get("has_more", False),
                "request_id": result.get("request_id"),
            }
            
        except ApiException as e:
            error_msg = f"Plaid API error syncing transactions: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidAPIError(
                message=error_msg,
                error_code=getattr(e, "error_code", None)
            )
        except Exception as e:
            error_msg = f"Unexpected error syncing transactions: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidServiceError(message=error_msg)
    
    def sync_all_transactions(
        self,
        access_token: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Sync all available transactions, handling pagination automatically.
        
        This is a convenience method that calls sync_transactions repeatedly
        until all available data has been fetched (has_more = False).
        
        Args:
            access_token: Access token for the Plaid Item
            cursor: Optional cursor from previous sync
            
        Returns:
            Dictionary containing:
                - added: Aggregated list of all added transactions
                - modified: Aggregated list of all modified transactions
                - removed: Aggregated list of all removed transaction objects
                - next_cursor: Final cursor for future syncs
                - total_synced: Total number of transactions synced
                - request_id: Last Plaid request ID
                
        Raises:
            PlaidAPIError: If the Plaid API returns an error
            PlaidServiceError: For other service-level errors
            
        Example:
            >>> service = PlaidService()
            >>> result = service.sync_all_transactions("access-sandbox-xxx")
            >>> print(f"Total synced: {result['total_synced']}")
            >>> # Save cursor for next sync
            >>> cursor = result["next_cursor"]
        """
        try:
            logger.info("Starting full transaction sync")
            
            all_added = []
            all_modified = []
            all_removed = []
            current_cursor = cursor
            last_request_id = None
            iteration = 0
            
            while True:
                iteration += 1
                result = self.sync_transactions(
                    access_token=access_token,
                    cursor=current_cursor,
                )
                
                all_added.extend(result["added"])
                all_modified.extend(result["modified"])
                all_removed.extend(result["removed"])
                current_cursor = result["next_cursor"]
                last_request_id = result.get("request_id")
                
                logger.info(
                    f"Sync iteration {iteration}: "
                    f"added={len(result['added'])}, "
                    f"modified={len(result['modified'])}, "
                    f"removed={len(result['removed'])}, "
                    f"has_more={result['has_more']}"
                )
                
                if not result["has_more"]:
                    break
            
            total_synced = len(all_added) + len(all_modified) + len(all_removed)
            
            logger.info(
                f"Full transaction sync complete, "
                f"total_synced: {total_synced}, "
                f"iterations: {iteration}"
            )
            
            return {
                "added": all_added,
                "modified": all_modified,
                "removed": all_removed,
                "next_cursor": current_cursor,
                "total_synced": total_synced,
                "request_id": last_request_id,
            }
            
        except PlaidAPIError:
            raise
        except PlaidServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error in full transaction sync: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlaidServiceError(message=error_msg)


# Singleton instance for easy import
plaid_service = PlaidService()
