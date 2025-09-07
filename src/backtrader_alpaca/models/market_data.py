"""Pydantic models for market data structures."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict


class QuoteData(BaseModel):
    """Latest quote data for a symbol."""

    symbol: str = Field(..., description="Stock symbol")
    bid: Decimal = Field(..., description="Bid price")
    ask: Decimal = Field(..., description="Ask price")
    bid_size: int = Field(..., description="Bid size")
    ask_size: int = Field(..., description="Ask size")
    timestamp: datetime = Field(..., description="Quote timestamp")

    @field_validator("bid", "ask", mode="before")
    @classmethod
    def validate_prices(cls, v: Any) -> Decimal:
        """Convert prices to Decimal for precision."""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    model_config = ConfigDict(json_encoders={Decimal: lambda v: float(v)})


class BarData(BaseModel):
    """Historical bar data for a symbol."""

    symbol: str = Field(..., description="Stock symbol")
    timestamp: datetime = Field(..., description="Bar timestamp")
    open: Decimal = Field(..., description="Opening price")
    high: Decimal = Field(..., description="High price")
    low: Decimal = Field(..., description="Low price")
    close: Decimal = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def validate_prices(cls, v: Any) -> Decimal:
        """Convert prices to Decimal for precision."""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    model_config = ConfigDict(json_encoders={Decimal: lambda v: float(v)})


class AssetData(BaseModel):
    """Tradable asset information."""

    symbol: str = Field(..., description="Asset symbol")
    name: str = Field(..., description="Asset name")
    exchange: str = Field(..., description="Exchange name")
    asset_class: Literal["us_equity", "crypto", "forex"] = Field(
        ..., description="Asset class"
    )
    tradable: bool = Field(..., description="Whether asset is tradable")

    model_config = ConfigDict()


class MarketData(BaseModel):
    """General market data model."""

    symbol: str = Field(..., description="Asset symbol")
    timestamp: datetime = Field(..., description="Data timestamp")
    open_price: Decimal = Field(..., description="Opening price")
    high_price: Decimal = Field(..., description="High price")
    low_price: Decimal = Field(..., description="Low price")
    close_price: Decimal = Field(..., description="Closing price")
    volume: int = Field(default=0, description="Trading volume")

    @field_validator(
        "open_price", "high_price", "low_price", "close_price", mode="before"
    )
    @classmethod
    def validate_prices(cls, v: Any) -> Decimal:
        """Convert prices to Decimal for precision."""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    model_config = ConfigDict(json_encoders={Decimal: lambda v: float(v)})


class Quote(BaseModel):
    """Quote data model."""

    symbol: str = Field(..., description="Asset symbol")
    bid_price: Decimal = Field(..., description="Bid price")
    ask_price: Decimal = Field(..., description="Ask price")
    bid_size: int = Field(..., description="Bid size")
    ask_size: int = Field(..., description="Ask size")
    timestamp: datetime = Field(..., description="Quote timestamp")

    @field_validator("bid_price", "ask_price", mode="before")
    @classmethod
    def validate_prices(cls, v: Any) -> Decimal:
        """Convert prices to Decimal for precision."""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    model_config = ConfigDict(json_encoders={Decimal: lambda v: float(v)})


class Trade(BaseModel):
    """Trade execution data model."""

    symbol: str = Field(..., description="Asset symbol")
    price: Decimal = Field(..., description="Trade price")
    size: int = Field(..., description="Trade size")
    timestamp: datetime = Field(..., description="Trade timestamp")
    conditions: list[str] = Field(default_factory=list, description="Trade conditions")

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v: Any) -> Decimal:
        """Convert price to Decimal for precision."""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    model_config = ConfigDict(json_encoders={Decimal: lambda v: float(v)})
