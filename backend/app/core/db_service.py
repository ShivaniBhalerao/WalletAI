"""
DatabaseService - Service for database operations with upsert logic.

This service handles all database operations for Plaid integration including:
- Creating and managing PlaidItem records
- Upserting accounts from Plaid data
- Upserting transactions from Plaid data
- Managing sync cursors
- Handling removed transactions
"""

import logging
import uuid
from datetime import date, datetime
from typing import Any

from sqlmodel import Session, select

from app.models import (
    Account,
    AccountCreate,
    PlaidItem,
    PlaidItemCreate,
    PlaidItemUpdate,
    Transaction,
    TransactionCreate,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseServiceError(Exception):
    """Base exception for database service errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class DatabaseService:
    """
    Service class for database operations related to Plaid integration.
    
    This service provides methods for:
    - Creating and retrieving PlaidItem records
    - Upserting accounts with deduplication by plaid_account_id
    - Upserting transactions with deduplication by plaid_transaction_id
    - Updating sync cursors for incremental syncs
    - Deleting removed transactions
    
    All methods include comprehensive error handling and logging.
    """
    
    def __init__(self, session: Session) -> None:
        """
        Initialize the DatabaseService with a database session.
        
        Args:
            session: SQLModel database session
        """
        self.session = session
        logger.info("DatabaseService initialized")
    
    def create_plaid_item(
        self,
        user_id: uuid.UUID,
        item_id: str,
        access_token: str,
        institution_name: str,
    ) -> PlaidItem:
        """
        Create a new PlaidItem record.
        
        Args:
            user_id: ID of the user who owns this item
            item_id: Plaid item identifier
            access_token: Encrypted Plaid access token
            institution_name: Name of the financial institution
            
        Returns:
            Created PlaidItem instance
            
        Raises:
            DatabaseServiceError: If creation fails
            
        Example:
            >>> db_service = DatabaseService(session)
            >>> plaid_item = db_service.create_plaid_item(
            ...     user_id=uuid.uuid4(),
            ...     item_id="item-123",
            ...     access_token="access-sandbox-xxx",
            ...     institution_name="Chase Bank"
            ... )
        """
        try:
            logger.info(
                f"Creating PlaidItem for user_id: {user_id}, "
                f"item_id: {item_id}, institution: {institution_name}"
            )
            
            plaid_item_create = PlaidItemCreate(
                item_id=item_id,
                access_token=access_token,
                institution_name=institution_name,
            )
            
            plaid_item = PlaidItem.model_validate(
                plaid_item_create,
                update={"user_id": user_id}
            )
            
            self.session.add(plaid_item)
            self.session.commit()
            self.session.refresh(plaid_item)
            
            logger.info(
                f"PlaidItem created successfully, id: {plaid_item.id}"
            )
            
            return plaid_item
            
        except Exception as e:
            self.session.rollback()
            error_msg = f"Error creating PlaidItem: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
    
    def get_plaid_items_for_user(self, user_id: uuid.UUID) -> list[PlaidItem]:
        """
        Retrieve all PlaidItems for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of PlaidItem instances
            
        Raises:
            DatabaseServiceError: If retrieval fails
            
        Example:
            >>> db_service = DatabaseService(session)
            >>> items = db_service.get_plaid_items_for_user(user_id)
            >>> for item in items:
            ...     print(f"{item.institution_name}: {item.item_id}")
        """
        try:
            logger.info(f"Retrieving PlaidItems for user_id: {user_id}")
            
            statement = select(PlaidItem).where(PlaidItem.user_id == user_id)
            plaid_items = list(self.session.exec(statement).all())
            
            logger.info(
                f"Retrieved {len(plaid_items)} PlaidItems for user_id: {user_id}"
            )
            
            return plaid_items
            
        except Exception as e:
            error_msg = f"Error retrieving PlaidItems: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
    
    def get_plaid_item_by_id(self, plaid_item_id: uuid.UUID) -> PlaidItem | None:
        """
        Retrieve a PlaidItem by its ID.
        
        Args:
            plaid_item_id: ID of the PlaidItem
            
        Returns:
            PlaidItem instance or None if not found
            
        Raises:
            DatabaseServiceError: If retrieval fails
        """
        try:
            logger.info(f"Retrieving PlaidItem with id: {plaid_item_id}")
            
            statement = select(PlaidItem).where(PlaidItem.id == plaid_item_id)
            plaid_item = self.session.exec(statement).first()
            
            if plaid_item:
                logger.info(f"PlaidItem found: {plaid_item.institution_name}")
            else:
                logger.warning(f"PlaidItem not found with id: {plaid_item_id}")
            
            return plaid_item
            
        except Exception as e:
            error_msg = f"Error retrieving PlaidItem: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
    
    def upsert_accounts(
        self,
        accounts: list[dict[str, Any]],
        plaid_item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[Account]:
        """
        Upsert accounts from Plaid data.
        
        This method performs insert or update operations based on plaid_account_id.
        If an account with the same plaid_account_id exists, it is updated.
        Otherwise, a new account is created.
        
        Args:
            accounts: List of account dictionaries from Plaid API
            plaid_item_id: ID of the associated PlaidItem
            user_id: ID of the user who owns these accounts
            
        Returns:
            List of upserted Account instances
            
        Raises:
            DatabaseServiceError: If upsert fails
            
        Example:
            >>> accounts_data = [
            ...     {
            ...         "account_id": "account-1",
            ...         "name": "Checking",
            ...         "official_name": "Plaid Checking",
            ...         "type": "depository",
            ...         "balances": {"current": 100.0, "iso_currency_code": "USD"}
            ...     }
            ... ]
            >>> db_service = DatabaseService(session)
            >>> accounts = db_service.upsert_accounts(
            ...     accounts_data, plaid_item_id, user_id
            ... )
        """
        try:
            logger.info(
                f"Upserting {len(accounts)} accounts for "
                f"plaid_item_id: {plaid_item_id}"
            )
            
            upserted_accounts = []
            
            for account_data in accounts:
                plaid_account_id = account_data.get("account_id")
                
                if not plaid_account_id:
                    logger.warning("Skipping account without account_id")
                    continue
                
                # Check if account already exists
                statement = select(Account).where(
                    Account.plaid_account_id == plaid_account_id
                )
                existing_account = self.session.exec(statement).first()
                
                # Extract account details
                name = account_data.get("name", "")
                official_name = account_data.get("official_name", name)
                account_type = account_data.get("type", "")
                balances = account_data.get("balances", {})
                current_balance = balances.get("current", 0.0)
                currency = balances.get("iso_currency_code", "USD")
                
                if existing_account:
                    # Update existing account
                    logger.info(
                        f"Updating existing account: {plaid_account_id}"
                    )
                    
                    existing_account.name = name
                    existing_account.official_name = official_name
                    existing_account.type = account_type
                    existing_account.current_balance = current_balance
                    existing_account.currency = currency
                    
                    self.session.add(existing_account)
                    upserted_accounts.append(existing_account)
                else:
                    # Create new account
                    logger.info(
                        f"Creating new account: {plaid_account_id}"
                    )
                    
                    account = Account(
                        user_id=user_id,
                        plaid_item_id=plaid_item_id,
                        plaid_account_id=plaid_account_id,
                        name=name,
                        official_name=official_name,
                        type=account_type,
                        current_balance=current_balance,
                        currency=currency,
                    )
                    
                    self.session.add(account)
                    upserted_accounts.append(account)
            
            self.session.commit()
            
            # Refresh all accounts to get IDs
            for account in upserted_accounts:
                self.session.refresh(account)
            
            logger.info(
                f"Successfully upserted {len(upserted_accounts)} accounts"
            )
            
            return upserted_accounts
            
        except Exception as e:
            self.session.rollback()
            error_msg = f"Error upserting accounts: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
    
    def upsert_transactions(
        self,
        transactions: list[dict[str, Any]],
        account_mapping: dict[str, uuid.UUID],
    ) -> list[Transaction]:
        """
        Upsert transactions from Plaid data.
        
        This method performs insert or update operations based on plaid_transaction_id.
        If a transaction with the same plaid_transaction_id exists, it is updated.
        Otherwise, a new transaction is created.
        
        Args:
            transactions: List of transaction dictionaries from Plaid API
            account_mapping: Mapping from plaid_account_id to Account.id
            
        Returns:
            List of upserted Transaction instances
            
        Raises:
            DatabaseServiceError: If upsert fails
            
        Example:
            >>> transactions_data = [
            ...     {
            ...         "transaction_id": "txn-1",
            ...         "account_id": "account-1",
            ...         "amount": 25.50,
            ...         "date": "2024-01-15",
            ...         "merchant_name": "Starbucks",
            ...         "pending": False,
            ...         "category": ["Food and Drink", "Restaurants"],
            ...     }
            ... ]
            >>> account_mapping = {"account-1": uuid.uuid4()}
            >>> db_service = DatabaseService(session)
            >>> transactions = db_service.upsert_transactions(
            ...     transactions_data, account_mapping
            ... )
        """
        try:
            logger.info(
                f"Upserting {len(transactions)} transactions"
            )
            
            upserted_transactions = []
            
            for txn_data in transactions:
                plaid_transaction_id = txn_data.get("transaction_id")
                plaid_account_id = txn_data.get("account_id")
                
                if not plaid_transaction_id:
                    logger.warning("Skipping transaction without transaction_id")
                    continue
                
                if not plaid_account_id or plaid_account_id not in account_mapping:
                    logger.warning(
                        f"Skipping transaction {plaid_transaction_id}: "
                        f"account_id {plaid_account_id} not found in mapping"
                    )
                    continue
                
                account_id = account_mapping[plaid_account_id]
                
                # Check if transaction already exists
                statement = select(Transaction).where(
                    Transaction.plaid_transaction_id == plaid_transaction_id
                )
                existing_transaction = self.session.exec(statement).first()
                
                # Extract transaction details
                amount = txn_data.get("amount", 0.0)
                
                # Parse date
                date_str = txn_data.get("date")
                if isinstance(date_str, str):
                    auth_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                elif isinstance(date_str, date):
                    auth_date = date_str
                else:
                    auth_date = date.today()
                
                merchant_name = txn_data.get("merchant_name") or txn_data.get("name", "Unknown")
                pending = txn_data.get("pending", False)
                
                # Extract category
                categories = txn_data.get("category", [])
                if isinstance(categories, list) and categories:
                    category = ", ".join(categories)
                else:
                    category = txn_data.get("personal_finance_category", {}).get("primary", "Other")
                
                currency = txn_data.get("iso_currency_code", "USD")
                
                if existing_transaction:
                    # Update existing transaction
                    logger.debug(
                        f"Updating existing transaction: {plaid_transaction_id}"
                    )
                    
                    existing_transaction.amount = amount
                    existing_transaction.auth_date = auth_date
                    existing_transaction.merchant_name = merchant_name
                    existing_transaction.pending = pending
                    existing_transaction.category = category
                    existing_transaction.currency = currency
                    
                    self.session.add(existing_transaction)
                    upserted_transactions.append(existing_transaction)
                else:
                    # Create new transaction
                    logger.debug(
                        f"Creating new transaction: {plaid_transaction_id}"
                    )
                    
                    transaction = Transaction(
                        account_id=account_id,
                        plaid_transaction_id=plaid_transaction_id,
                        amount=amount,
                        auth_date=auth_date,
                        merchant_name=merchant_name,
                        pending=pending,
                        category=category,
                        currency=currency,
                    )
                    
                    self.session.add(transaction)
                    upserted_transactions.append(transaction)
            
            self.session.commit()
            
            # Refresh all transactions to get IDs
            for transaction in upserted_transactions:
                self.session.refresh(transaction)
            
            logger.info(
                f"Successfully upserted {len(upserted_transactions)} transactions"
            )
            
            return upserted_transactions
            
        except Exception as e:
            self.session.rollback()
            error_msg = f"Error upserting transactions: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
    
    def update_sync_cursor(
        self,
        plaid_item_id: uuid.UUID,
        cursor: str,
    ) -> PlaidItem:
        """
        Update the sync cursor for a PlaidItem.
        
        The cursor is used for incremental transaction syncs to avoid
        re-fetching all historical data.
        
        Args:
            plaid_item_id: ID of the PlaidItem to update
            cursor: New cursor value from Plaid Transactions Sync API
            
        Returns:
            Updated PlaidItem instance
            
        Raises:
            DatabaseServiceError: If update fails or PlaidItem not found
            
        Example:
            >>> db_service = DatabaseService(session)
            >>> plaid_item = db_service.update_sync_cursor(
            ...     plaid_item_id, "cursor-abc123"
            ... )
        """
        try:
            logger.info(
                f"Updating sync cursor for plaid_item_id: {plaid_item_id}"
            )
            
            statement = select(PlaidItem).where(PlaidItem.id == plaid_item_id)
            plaid_item = self.session.exec(statement).first()
            
            if not plaid_item:
                raise DatabaseServiceError(
                    f"PlaidItem not found with id: {plaid_item_id}"
                )
            
            plaid_item.cursor = cursor
            
            self.session.add(plaid_item)
            self.session.commit()
            self.session.refresh(plaid_item)
            
            logger.info(
                f"Sync cursor updated successfully for plaid_item_id: {plaid_item_id}"
            )
            
            return plaid_item
            
        except DatabaseServiceError:
            raise
        except Exception as e:
            self.session.rollback()
            error_msg = f"Error updating sync cursor: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
    
    def delete_transactions(
        self,
        transaction_ids: list[str],
    ) -> int:
        """
        Delete transactions by their Plaid transaction IDs.
        
        This is used to handle removed transactions from Plaid's Transactions
        Sync API response.
        
        Args:
            transaction_ids: List of Plaid transaction IDs to delete
            
        Returns:
            Number of transactions deleted
            
        Raises:
            DatabaseServiceError: If deletion fails
            
        Example:
            >>> db_service = DatabaseService(session)
            >>> count = db_service.delete_transactions(["txn-old-1", "txn-old-2"])
            >>> print(f"Deleted {count} transactions")
        """
        try:
            if not transaction_ids:
                logger.info("No transactions to delete")
                return 0
            
            logger.info(
                f"Deleting {len(transaction_ids)} transactions"
            )
            
            statement = select(Transaction).where(
                Transaction.plaid_transaction_id.in_(transaction_ids)
            )
            transactions = list(self.session.exec(statement).all())
            
            for transaction in transactions:
                self.session.delete(transaction)
            
            self.session.commit()
            
            deleted_count = len(transactions)
            logger.info(
                f"Successfully deleted {deleted_count} transactions"
            )
            
            return deleted_count
            
        except Exception as e:
            self.session.rollback()
            error_msg = f"Error deleting transactions: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
    
    def get_account_by_plaid_id(
        self,
        plaid_account_id: str,
    ) -> Account | None:
        """
        Retrieve an Account by its Plaid account ID.
        
        Args:
            plaid_account_id: Plaid account identifier
            
        Returns:
            Account instance or None if not found
            
        Raises:
            DatabaseServiceError: If retrieval fails
        """
        try:
            statement = select(Account).where(
                Account.plaid_account_id == plaid_account_id
            )
            account = self.session.exec(statement).first()
            
            return account
            
        except Exception as e:
            error_msg = f"Error retrieving account: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseServiceError(message=error_msg)
