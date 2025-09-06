"""Pydantic models for account-related data structures."""

from typing import Any
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

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

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: lambda v: float(v),
            UUID: lambda v: str(v)
        }
