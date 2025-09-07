"""Pydantic models for account-related data structures."""

from typing import Any, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

class AccountInfo(BaseModel):
    """Account information from Alpaca API."""

    id: UUID = Field(..., description="Account ID")
    buying_power: Decimal = Field(..., description="Available buying power in USD")
    cash: Decimal = Field(..., description="Available cash in USD")
    portfolio_value: Decimal = Field(..., description="Total portfolio value in USD")
    status: str = Field(description="Account status")

    @field_validator('buying_power', 'cash', 'portfolio_value', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal:
        """Convert string or numeric values to Decimal."""
        if v is None:
            return Decimal('0')
        return Decimal(str(v))

    @field_validator('id', mode='before')
    @classmethod
    def validate_uuid_field(cls, v: Any) -> UUID:
        """Convert string to UUID."""
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v),
            UUID: lambda v: str(v)
        }
    )


class Account(BaseModel):
    """Account model for testing and API interactions."""
    
    id: str = Field(..., description="Account ID")
    account_number: str = Field(..., description="Account number")
    status: str = Field(..., description="Account status")
    currency: str = Field(default="USD", description="Account currency")
    buying_power: Decimal = Field(..., description="Available buying power")
    cash: Decimal = Field(..., description="Available cash")
    portfolio_value: Decimal = Field(..., description="Total portfolio value")
    day_trade_count: int = Field(default=0, description="Number of day trades")
    pattern_day_trader: bool = Field(default=False, description="Pattern day trader status")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v: Any) -> str:
        """Validate account ID is not empty."""
        if not v or str(v).strip() == "":
            raise ValueError("Account ID cannot be empty")
        return str(v)
    
    @field_validator('buying_power', 'cash', 'portfolio_value', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal:
        """Convert string or numeric values to Decimal."""
        if v is None:
            return Decimal('0')
        return Decimal(str(v))

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)}
    )


class Position(BaseModel):
    """Position model for portfolio positions."""
    
    symbol: str = Field(..., description="Asset symbol")
    quantity: Decimal = Field(..., description="Quantity held")
    side: str = Field(..., description="Position side (long/short)")
    market_value: Decimal = Field(..., description="Current market value")
    cost_basis: Decimal = Field(..., description="Cost basis")
    unrealized_pl: Decimal = Field(..., description="Unrealized P&L")
    unrealized_plpc: Optional[Decimal] = Field(None, description="Unrealized P&L percentage")
    avg_entry_price: Optional[Decimal] = Field(None, description="Average entry price")
    change_today: Optional[Decimal] = Field(None, description="Change today")
    
    @field_validator('quantity', 'market_value', 'cost_basis', 'unrealized_pl', 
                     'unrealized_plpc', 'avg_entry_price', 'change_today', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal:
        """Convert string or numeric values to Decimal."""
        if v is None:
            return Decimal('0')
        return Decimal(str(v))

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)}
    )
