import uuid
from datetime import date

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    accounts: list["Account"] = Relationship(back_populates="user", cascade_delete=True)
    plaid_items: list["PlaidItem"] = Relationship(back_populates="user", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties for PlaidItem
class PlaidItemBase(SQLModel):
    """Base model for Plaid item representing a bank connection."""
    item_id: str = Field(max_length=255, index=True)
    institution_name: str = Field(max_length=255)
    access_token: str = Field(max_length=512)  # Encrypted Plaid access token
    cursor: str | None = Field(default=None, max_length=512)  # Sync cursor for incremental updates


# Properties to receive on PlaidItem creation
class PlaidItemCreate(PlaidItemBase):
    """Schema for creating a new Plaid item."""
    pass


# Properties to receive on PlaidItem update
class PlaidItemUpdate(SQLModel):
    """Schema for updating a Plaid item."""
    institution_name: str | None = Field(default=None, max_length=255)  # type: ignore
    access_token: str | None = Field(default=None, max_length=512)  # type: ignore
    cursor: str | None = Field(default=None, max_length=512)  # type: ignore


# Database model, database table inferred from class name
class PlaidItem(PlaidItemBase, table=True):
    """
    Database model for storing Plaid access tokens and sync state.
    Represents a connection between a user and a financial institution via Plaid.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    user: User | None = Relationship(back_populates="plaid_items")
    accounts: list["Account"] = Relationship(back_populates="plaid_item", cascade_delete=True)


# Properties to return via API, id is always required
class PlaidItemPublic(SQLModel):
    """Public schema for PlaidItem (excludes sensitive access_token)."""
    id: uuid.UUID
    user_id: uuid.UUID
    item_id: str
    institution_name: str
    cursor: str | None


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# Shared properties
class AccountBase(SQLModel):
    name: str = Field(max_length=255)
    official_name: str = Field(max_length=255)
    type: str = Field(max_length=255)
    current_balance: float = Field(default=0.0)
    currency: str = Field(max_length=255)
    plaid_account_id: str | None = Field(default=None, max_length=255, unique=True, index=True)


# Properties to receive on account creation
class AccountCreate(AccountBase):
    pass


# Properties to receive on account update
class AccountUpdate(AccountBase):
    name: str | None = Field(default=None, max_length=255)  # type: ignore
    official_name: str | None = Field(default=None, max_length=255)  # type: ignore
    type: str | None = Field(default=None, max_length=255)  # type: ignore
    current_balance: float | None = Field(default=None)
    currency: str | None = Field(default=None, max_length=255)  # type: ignore
    plaid_account_id: str | None = Field(default=None, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Account(AccountBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    plaid_item_id: uuid.UUID | None = Field(
        default=None, foreign_key="plaiditem.id", nullable=True, ondelete="CASCADE", index=True
    )
    user: User | None = Relationship(back_populates="accounts")
    plaid_item: PlaidItem | None = Relationship(back_populates="accounts")
    transactions: list["Transaction"] = Relationship(back_populates="account", cascade_delete=True)


# Properties to return via API, id is always required
class AccountPublic(AccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    plaid_item_id: uuid.UUID | None
    name: str
    official_name: str
    type: str
    current_balance: float
    currency: str
    plaid_account_id: str | None


# Shared properties
class TransactionBase(SQLModel):
    amount: float
    auth_date: date
    merchant_name: str = Field(max_length=255)
    pending: bool = Field(default=False)
    category: str = Field(max_length=255)
    currency: str = Field(max_length=10, default="USD")
    plaid_transaction_id: str | None = Field(default=None, max_length=255, unique=True, index=True)


# Properties to receive on transaction creation
class TransactionCreate(TransactionBase):
    pass


# Properties to receive on transaction update
class TransactionUpdate(TransactionBase):
    amount: float | None = Field(default=None)
    auth_date: date | None = Field(default=None)
    merchant_name: str | None = Field(default=None, max_length=255)  # type: ignore
    pending: bool | None = Field(default=None)
    category: str | None = Field(default=None, max_length=255)  # type: ignore
    currency: str | None = Field(default=None, max_length=10)  # type: ignore
    plaid_transaction_id: str | None = Field(default=None, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Transaction(TransactionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(
        foreign_key="account.id", nullable=False, ondelete="CASCADE"
    )
    account: Account | None = Relationship(back_populates="transactions")


# Properties to return via API, id is always required
class TransactionPublic(TransactionBase):
    id: uuid.UUID
    account_id: uuid.UUID
    amount: float
    auth_date: date
    merchant_name: str
    pending: bool
    category: str
    currency: str
    plaid_transaction_id: str | None


# Plaid API response models
class PlaidLinkTokenResponse(SQLModel):
    """Response model for Plaid Link token creation."""
    link_token: str
    expiration: str


class PlaidExchangeRequest(SQLModel):
    """Request model for exchanging Plaid public token."""
    public_token: str
    institution_name: str


class PlaidSyncResponse(SQLModel):
    """Response model for Plaid transaction sync operation."""
    total_added: int
    total_modified: int
    total_removed: int
    items_synced: int


class PlaidStatusResponse(SQLModel):
    """Response model for Plaid connection status."""
    is_connected: bool
    items: list[PlaidItemPublic]