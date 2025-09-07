"""Options data models for chain retrieval and Greeks calculations."""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict


class OptionType(str, Enum):
    """Option type enumeration."""

    CALL = "call"
    PUT = "put"


class OptionStyle(str, Enum):
    """Option exercise style."""

    AMERICAN = "american"
    EUROPEAN = "european"


class OptionContract(BaseModel):
    """Individual option contract data."""

    symbol: str = Field(..., description="Option contract symbol")
    underlying_symbol: str = Field(..., description="Underlying asset symbol")
    option_type: OptionType = Field(..., description="Call or Put")
    strike_price: Decimal = Field(..., description="Strike price")
    expiration_date: date = Field(..., description="Expiration date")

    # Market data
    bid_price: Optional[Decimal] = Field(None, description="Current bid price")
    ask_price: Optional[Decimal] = Field(None, description="Current ask price")
    last_price: Optional[Decimal] = Field(None, description="Last traded price")
    volume: Optional[int] = Field(None, description="Trading volume")
    open_interest: Optional[int] = Field(None, description="Open interest")

    # Greeks
    delta: Optional[Decimal] = Field(None, description="Delta Greek")
    gamma: Optional[Decimal] = Field(None, description="Gamma Greek")
    theta: Optional[Decimal] = Field(None, description="Theta Greek")
    vega: Optional[Decimal] = Field(None, description="Vega Greek")
    rho: Optional[Decimal] = Field(None, description="Rho Greek")

    # Volatility
    implied_volatility: Optional[Decimal] = Field(
        None, description="Implied volatility"
    )

    # Timestamps
    quote_timestamp: Optional[datetime] = Field(None, description="Quote timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    @field_validator(
        "strike_price", "bid_price", "ask_price", "last_price", mode="before"
    )
    @classmethod
    def validate_positive_prices(cls, v):
        """Validate that prices are positive."""
        if v is not None and v < 0:
            raise ValueError("Prices must be non-negative")
        return v

    @field_validator("volume", "open_interest", mode="before")
    @classmethod
    def validate_non_negative_integers(cls, v):
        """Validate that volume and open interest are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Volume and open interest must be non-negative")
        return v

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v),
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
    )


class OptionsChain(BaseModel):
    """Complete options chain for an underlying symbol."""

    underlying_symbol: str = Field(..., description="Underlying asset symbol")
    underlying_price: Optional[Decimal] = Field(
        None, description="Current underlying price"
    )

    # Chain data
    calls: List[OptionContract] = Field(
        default_factory=list, description="Call options"
    )
    puts: List[OptionContract] = Field(default_factory=list, description="Put options")

    # Metadata
    chain_timestamp: Optional[datetime] = Field(
        None, description="Chain retrieval timestamp"
    )
    expiration_dates: List[date] = Field(
        default_factory=list, description="Available expiration dates"
    )
    strike_prices: List[Decimal] = Field(
        default_factory=list, description="Available strike prices"
    )

    @field_validator("underlying_price", mode="before")
    @classmethod
    def validate_underlying_price(cls, v):
        """Validate underlying price is positive."""
        if v is not None and v <= 0:
            raise ValueError("Underlying price must be positive")
        return v

    def get_contracts_by_expiration(self, expiration: date) -> List[OptionContract]:
        """Get all contracts for a specific expiration date."""
        return [
            contract
            for contract in (self.calls + self.puts)
            if contract.expiration_date == expiration
        ]

    def get_contracts_by_strike(self, strike: Decimal) -> List[OptionContract]:
        """Get all contracts for a specific strike price."""
        return [
            contract
            for contract in (self.calls + self.puts)
            if contract.strike_price == strike
        ]

    def get_atm_contracts(
        self, tolerance: Decimal = Decimal("0.05")
    ) -> List[OptionContract]:
        """Get at-the-money contracts within tolerance."""
        if not self.underlying_price:
            return []

        return [
            contract
            for contract in (self.calls + self.puts)
            if abs(contract.strike_price - self.underlying_price)
            / self.underlying_price
            <= tolerance
        ]

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
    )


# Greeks calculation models removed - using API data only


class HistoricalOptionsData(BaseModel):
    """Historical options pricing data point."""

    symbol: str = Field(..., description="Option contract symbol")
    timestamp: datetime = Field(..., description="Data timestamp")

    # OHLCV data
    open_price: Optional[Decimal] = Field(None, description="Opening price")
    high_price: Optional[Decimal] = Field(None, description="High price")
    low_price: Optional[Decimal] = Field(None, description="Low price")
    close_price: Optional[Decimal] = Field(None, description="Closing price")
    volume: Optional[int] = Field(None, description="Trading volume")

    # Greeks historical data
    delta: Optional[Decimal] = Field(None, description="Historical delta")
    gamma: Optional[Decimal] = Field(None, description="Historical gamma")
    theta: Optional[Decimal] = Field(None, description="Historical theta")
    vega: Optional[Decimal] = Field(None, description="Historical vega")
    rho: Optional[Decimal] = Field(None, description="Historical rho")

    # Volatility data
    implied_volatility: Optional[Decimal] = Field(
        None, description="Historical implied volatility"
    )

    @field_validator(
        "open_price", "high_price", "low_price", "close_price", mode="before"
    )
    @classmethod
    def validate_prices(cls, v):
        """Validate prices are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Prices must be non-negative")
        return v

    @field_validator("volume", mode="before")
    @classmethod
    def validate_volume(cls, v):
        """Validate volume is non-negative."""
        if v is not None and v < 0:
            raise ValueError("Volume must be non-negative")
        return v

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v), datetime: lambda v: v.isoformat()}
    )
