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
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    accounts: list["Account"] = Relationship(back_populates="user", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


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


# Database model, database table inferred from class name
class Account(AccountBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    user: User | None = Relationship(back_populates="accounts")
    transactions: list["Transaction"] = Relationship(back_populates="account", cascade_delete=True)


# Properties to return via API, id is always required
class AccountPublic(AccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    official_name: str
    type: str
    current_balance: float
    currency: str


# Shared properties
class TransactionBase(SQLModel):
    amount: float
    auth_date: date
    merchant_name: str = Field(max_length=255)
    pending: bool = Field(default=False)
    category: str = Field(max_length=255)
    currency: str = Field(max_length=10, default="USD")


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