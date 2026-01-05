"""
Unit tests for PlaidService.

Tests all methods of PlaidService with proper mocking of Plaid API responses.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from plaid import ApiException

from app.core.plaid_service import (
    PlaidAPIError,
    PlaidService,
    PlaidServiceError,
)


@pytest.fixture
def plaid_service() -> PlaidService:
    """Create a PlaidService instance for testing."""
    # Mock plaid module before creating service
    with patch("plaid.Configuration"), \
         patch("plaid.ApiClient"), \
         patch("plaid.api.plaid_api.PlaidApi") as mock_plaid_api:
        service = PlaidService()
        # Replace the client with a mock after initialization
        service.client = MagicMock()
        return service


class TestCreateLinkToken:
    """Tests for create_link_token method."""
    
    def test_create_link_token_success(self, plaid_service: PlaidService) -> None:
        """Test successful link token creation."""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "link_token": "link-sandbox-test-token",
            "expiration": "2024-12-31T23:59:59Z",
            "request_id": "test-request-id-123",
        }
        plaid_service.client.link_token_create.return_value = mock_response
        
        # Call method
        result = plaid_service.create_link_token(user_id="user-123")
        
        # Assertions
        assert result["link_token"] == "link-sandbox-test-token"
        assert result["expiration"] == "2024-12-31T23:59:59Z"
        assert result["request_id"] == "test-request-id-123"
        
        # Verify API was called with correct parameters
        plaid_service.client.link_token_create.assert_called_once()
        call_args = plaid_service.client.link_token_create.call_args[0][0]
        assert call_args.user.client_user_id == "user-123"
        assert call_args.client_name == "WalletAI"
    
    def test_create_link_token_custom_client_name(
        self, plaid_service: PlaidService
    ) -> None:
        """Test link token creation with custom client name."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "link_token": "link-sandbox-test-token",
            "expiration": "2024-12-31T23:59:59Z",
            "request_id": "test-request-id-123",
        }
        plaid_service.client.link_token_create.return_value = mock_response
        
        result = plaid_service.create_link_token(
            user_id="user-123",
            client_name="CustomApp"
        )
        
        assert result["link_token"] == "link-sandbox-test-token"
        
        # Verify custom client name was used
        call_args = plaid_service.client.link_token_create.call_args[0][0]
        assert call_args.client_name == "CustomApp"
    
    def test_create_link_token_api_error(self, plaid_service: PlaidService) -> None:
        """Test link token creation with Plaid API error."""
        # Mock API exception
        plaid_service.client.link_token_create.side_effect = ApiException(
            status=400,
            reason="Bad Request"
        )
        
        # Should raise PlaidAPIError
        with pytest.raises(PlaidAPIError) as exc_info:
            plaid_service.create_link_token(user_id="user-123")
        
        assert "Plaid API error" in str(exc_info.value)
    
    def test_create_link_token_unexpected_error(
        self, plaid_service: PlaidService
    ) -> None:
        """Test link token creation with unexpected error."""
        plaid_service.client.link_token_create.side_effect = Exception(
            "Unexpected error"
        )
        
        with pytest.raises(PlaidServiceError) as exc_info:
            plaid_service.create_link_token(user_id="user-123")
        
        assert "Unexpected error" in str(exc_info.value)


class TestExchangePublicToken:
    """Tests for exchange_public_token method."""
    
    def test_exchange_public_token_success(
        self, plaid_service: PlaidService
    ) -> None:
        """Test successful public token exchange."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "access_token": "access-sandbox-test-token",
            "item_id": "item-test-123",
            "request_id": "test-request-id-456",
        }
        plaid_service.client.item_public_token_exchange.return_value = mock_response
        
        result = plaid_service.exchange_public_token(
            public_token="public-sandbox-test-token"
        )
        
        assert result["access_token"] == "access-sandbox-test-token"
        assert result["item_id"] == "item-test-123"
        assert result["request_id"] == "test-request-id-456"
        
        # Verify API was called
        plaid_service.client.item_public_token_exchange.assert_called_once()
    
    def test_exchange_public_token_api_error(
        self, plaid_service: PlaidService
    ) -> None:
        """Test public token exchange with API error."""
        plaid_service.client.item_public_token_exchange.side_effect = ApiException(
            status=400,
            reason="Invalid public token"
        )
        
        with pytest.raises(PlaidAPIError) as exc_info:
            plaid_service.exchange_public_token(
                public_token="invalid-token"
            )
        
        assert "Plaid API error" in str(exc_info.value)
    
    def test_exchange_public_token_unexpected_error(
        self, plaid_service: PlaidService
    ) -> None:
        """Test public token exchange with unexpected error."""
        plaid_service.client.item_public_token_exchange.side_effect = Exception(
            "Network error"
        )
        
        with pytest.raises(PlaidServiceError):
            plaid_service.exchange_public_token(
                public_token="public-token"
            )


class TestGetAccounts:
    """Tests for get_accounts method."""
    
    def test_get_accounts_success(self, plaid_service: PlaidService) -> None:
        """Test successful account retrieval."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "accounts": [
                {
                    "account_id": "account-1",
                    "name": "Plaid Checking",
                    "official_name": "Plaid Gold Standard 0% Interest Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "balances": {
                        "available": 100.0,
                        "current": 110.0,
                        "limit": None,
                        "iso_currency_code": "USD",
                    },
                },
                {
                    "account_id": "account-2",
                    "name": "Plaid Saving",
                    "official_name": "Plaid Silver Standard 0.1% Interest Saving",
                    "type": "depository",
                    "subtype": "savings",
                    "balances": {
                        "available": 200.0,
                        "current": 210.0,
                        "limit": None,
                        "iso_currency_code": "USD",
                    },
                },
            ],
            "item": {"item_id": "item-123"},
            "request_id": "test-request-id-789",
        }
        plaid_service.client.accounts_get.return_value = mock_response
        
        result = plaid_service.get_accounts(
            access_token="access-sandbox-test-token"
        )
        
        assert len(result["accounts"]) == 2
        assert result["accounts"][0]["account_id"] == "account-1"
        assert result["accounts"][0]["name"] == "Plaid Checking"
        assert result["accounts"][0]["type"] == "depository"
        assert result["accounts"][0]["balances"]["current"] == 110.0
        
        assert result["accounts"][1]["account_id"] == "account-2"
        assert result["item"]["item_id"] == "item-123"
        assert result["request_id"] == "test-request-id-789"
    
    def test_get_accounts_empty(self, plaid_service: PlaidService) -> None:
        """Test account retrieval with no accounts."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "accounts": [],
            "item": {"item_id": "item-123"},
            "request_id": "test-request-id",
        }
        plaid_service.client.accounts_get.return_value = mock_response
        
        result = plaid_service.get_accounts(
            access_token="access-sandbox-test-token"
        )
        
        assert len(result["accounts"]) == 0
    
    def test_get_accounts_api_error(self, plaid_service: PlaidService) -> None:
        """Test account retrieval with API error."""
        plaid_service.client.accounts_get.side_effect = ApiException(
            status=400,
            reason="Invalid access token"
        )
        
        with pytest.raises(PlaidAPIError):
            plaid_service.get_accounts(access_token="invalid-token")


class TestSyncTransactions:
    """Tests for sync_transactions method."""
    
    def test_sync_transactions_initial_sync(
        self, plaid_service: PlaidService
    ) -> None:
        """Test initial transaction sync without cursor."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "added": [
                {
                    "transaction_id": "txn-1",
                    "account_id": "account-1",
                    "amount": 25.50,
                    "date": "2024-01-15",
                    "merchant_name": "Starbucks",
                    "pending": False,
                },
                {
                    "transaction_id": "txn-2",
                    "account_id": "account-1",
                    "amount": 100.00,
                    "date": "2024-01-16",
                    "merchant_name": "Whole Foods",
                    "pending": False,
                },
            ],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-abc123",
            "has_more": False,
            "request_id": "test-request-id",
        }
        plaid_service.client.transactions_sync.return_value = mock_response
        
        result = plaid_service.sync_transactions(
            access_token="access-sandbox-test-token"
        )
        
        assert len(result["added"]) == 2
        assert len(result["modified"]) == 0
        assert len(result["removed"]) == 0
        assert result["next_cursor"] == "cursor-abc123"
        assert result["has_more"] is False
        
        # Verify first transaction
        assert result["added"][0]["transaction_id"] == "txn-1"
        assert result["added"][0]["amount"] == 25.50
        assert result["added"][0]["merchant_name"] == "Starbucks"
    
    def test_sync_transactions_with_cursor(
        self, plaid_service: PlaidService
    ) -> None:
        """Test transaction sync with existing cursor."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "added": [
                {
                    "transaction_id": "txn-3",
                    "account_id": "account-1",
                    "amount": 50.00,
                    "date": "2024-01-17",
                    "merchant_name": "Amazon",
                    "pending": True,
                },
            ],
            "modified": [
                {
                    "transaction_id": "txn-1",
                    "account_id": "account-1",
                    "amount": 25.50,
                    "date": "2024-01-15",
                    "merchant_name": "Starbucks",
                    "pending": False,
                },
            ],
            "removed": [
                {"transaction_id": "txn-old"},
            ],
            "next_cursor": "cursor-def456",
            "has_more": False,
            "request_id": "test-request-id",
        }
        plaid_service.client.transactions_sync.return_value = mock_response
        
        result = plaid_service.sync_transactions(
            access_token="access-sandbox-test-token",
            cursor="cursor-abc123"
        )
        
        assert len(result["added"]) == 1
        assert len(result["modified"]) == 1
        assert len(result["removed"]) == 1
        assert result["next_cursor"] == "cursor-def456"
        
        # Verify modified transaction
        assert result["modified"][0]["transaction_id"] == "txn-1"
        
        # Verify removed transaction
        assert result["removed"][0]["transaction_id"] == "txn-old"
    
    def test_sync_transactions_with_has_more(
        self, plaid_service: PlaidService
    ) -> None:
        """Test transaction sync with has_more flag."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "added": [{"transaction_id": f"txn-{i}"} for i in range(500)],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-next",
            "has_more": True,
            "request_id": "test-request-id",
        }
        plaid_service.client.transactions_sync.return_value = mock_response
        
        result = plaid_service.sync_transactions(
            access_token="access-sandbox-test-token"
        )
        
        assert len(result["added"]) == 500
        assert result["has_more"] is True
        assert result["next_cursor"] == "cursor-next"
    
    def test_sync_transactions_custom_count(
        self, plaid_service: PlaidService
    ) -> None:
        """Test transaction sync with custom count."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-abc",
            "has_more": False,
            "request_id": "test-request-id",
        }
        plaid_service.client.transactions_sync.return_value = mock_response
        
        plaid_service.sync_transactions(
            access_token="access-sandbox-test-token",
            count=100
        )
        
        # Verify count was passed correctly
        call_args = plaid_service.client.transactions_sync.call_args[0][0]
        assert call_args.count == 100
    
    def test_sync_transactions_api_error(
        self, plaid_service: PlaidService
    ) -> None:
        """Test transaction sync with API error."""
        plaid_service.client.transactions_sync.side_effect = ApiException(
            status=400,
            reason="Invalid access token"
        )
        
        with pytest.raises(PlaidAPIError):
            plaid_service.sync_transactions(
                access_token="invalid-token"
            )


class TestSyncAllTransactions:
    """Tests for sync_all_transactions method."""
    
    def test_sync_all_transactions_single_page(
        self, plaid_service: PlaidService
    ) -> None:
        """Test full sync with single page of results."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "added": [
                {"transaction_id": "txn-1"},
                {"transaction_id": "txn-2"},
            ],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-final",
            "has_more": False,
            "request_id": "test-request-id",
        }
        plaid_service.client.transactions_sync.return_value = mock_response
        
        result = plaid_service.sync_all_transactions(
            access_token="access-sandbox-test-token"
        )
        
        assert len(result["added"]) == 2
        assert result["total_synced"] == 2
        assert result["next_cursor"] == "cursor-final"
        
        # Should only call API once
        assert plaid_service.client.transactions_sync.call_count == 1
    
    def test_sync_all_transactions_multiple_pages(
        self, plaid_service: PlaidService
    ) -> None:
        """Test full sync with multiple pages of results."""
        # First call returns has_more=True
        first_response = Mock()
        first_response.to_dict.return_value = {
            "added": [{"transaction_id": f"txn-{i}"} for i in range(100)],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-page2",
            "has_more": True,
            "request_id": "test-request-id-1",
        }
        
        # Second call returns has_more=True
        second_response = Mock()
        second_response.to_dict.return_value = {
            "added": [{"transaction_id": f"txn-{i}"} for i in range(100, 200)],
            "modified": [{"transaction_id": "txn-0"}],
            "removed": [],
            "next_cursor": "cursor-page3",
            "has_more": True,
            "request_id": "test-request-id-2",
        }
        
        # Third call returns has_more=False
        third_response = Mock()
        third_response.to_dict.return_value = {
            "added": [{"transaction_id": f"txn-{i}"} for i in range(200, 250)],
            "modified": [],
            "removed": [{"transaction_id": "txn-old"}],
            "next_cursor": "cursor-final",
            "has_more": False,
            "request_id": "test-request-id-3",
        }
        
        plaid_service.client.transactions_sync.side_effect = [
            first_response,
            second_response,
            third_response,
        ]
        
        result = plaid_service.sync_all_transactions(
            access_token="access-sandbox-test-token"
        )
        
        # Should aggregate all results
        assert len(result["added"]) == 250
        assert len(result["modified"]) == 1
        assert len(result["removed"]) == 1
        assert result["total_synced"] == 252
        assert result["next_cursor"] == "cursor-final"
        
        # Should call API three times
        assert plaid_service.client.transactions_sync.call_count == 3
    
    def test_sync_all_transactions_with_initial_cursor(
        self, plaid_service: PlaidService
    ) -> None:
        """Test full sync with initial cursor."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "added": [{"transaction_id": "txn-new"}],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-updated",
            "has_more": False,
            "request_id": "test-request-id",
        }
        plaid_service.client.transactions_sync.return_value = mock_response
        
        result = plaid_service.sync_all_transactions(
            access_token="access-sandbox-test-token",
            cursor="cursor-existing"
        )
        
        assert len(result["added"]) == 1
        assert result["next_cursor"] == "cursor-updated"
    
    def test_sync_all_transactions_api_error(
        self, plaid_service: PlaidService
    ) -> None:
        """Test full sync with API error."""
        plaid_service.client.transactions_sync.side_effect = ApiException(
            status=400,
            reason="Invalid access token"
        )
        
        with pytest.raises(PlaidAPIError):
            plaid_service.sync_all_transactions(
                access_token="invalid-token"
            )
    
    def test_sync_all_transactions_propagates_service_error(
        self, plaid_service: PlaidService
    ) -> None:
        """Test that service errors are propagated."""
        plaid_service.client.transactions_sync.side_effect = Exception(
            "Network error"
        )
        
        with pytest.raises(PlaidServiceError):
            plaid_service.sync_all_transactions(
                access_token="access-token"
            )


class TestPlaidServiceErrors:
    """Tests for error handling and custom exceptions."""
    
    def test_plaid_service_error_basic(self) -> None:
        """Test basic PlaidServiceError."""
        error = PlaidServiceError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code is None
    
    def test_plaid_service_error_with_code(self) -> None:
        """Test PlaidServiceError with error code."""
        error = PlaidServiceError("Test error", error_code="INVALID_REQUEST")
        
        assert error.message == "Test error"
        assert error.error_code == "INVALID_REQUEST"
    
    def test_plaid_api_error_inheritance(self) -> None:
        """Test that PlaidAPIError inherits from PlaidServiceError."""
        error = PlaidAPIError("API error", error_code="ITEM_LOGIN_REQUIRED")
        
        assert isinstance(error, PlaidServiceError)
        assert error.message == "API error"
        assert error.error_code == "ITEM_LOGIN_REQUIRED"
