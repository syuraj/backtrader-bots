"""Risk management system for portfolio and position controls."""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RiskLevel(str, Enum):
    """Risk alert levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAlert(BaseModel):
    """Risk management alert."""

    level: RiskLevel = Field(..., description="Alert severity level")
    message: str = Field(..., description="Alert message")
    metric: str = Field(..., description="Risk metric that triggered alert")
    value: float = Field(..., description="Current metric value")
    threshold: float = Field(..., description="Risk threshold that was breached")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Alert timestamp"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class PositionLimits(BaseModel):
    """Position size and value limits."""

    max_position_size: Optional[int] = Field(
        None, gt=0, description="Maximum position size in shares"
    )
    max_position_value: Optional[Decimal] = Field(
        None, gt=0, description="Maximum position value in USD"
    )
    max_portfolio_concentration: Optional[Decimal] = Field(
        None, gt=0, lt=1, description="Max % of portfolio in single position"
    )

    @field_validator("max_portfolio_concentration")
    def validate_concentration(cls, v):
        """Validate concentration is between 0 and 1."""
        if v is not None and (v <= 0 or v >= 1):
            raise ValueError("Portfolio concentration must be between 0 and 1")
        return v


class DrawdownLimits(BaseModel):
    """Drawdown protection limits."""

    max_daily_loss: Optional[Decimal] = Field(
        None, gt=0, description="Maximum daily loss in USD"
    )
    max_daily_loss_pct: Optional[Decimal] = Field(
        None, gt=0, lt=1, description="Maximum daily loss as % of portfolio"
    )
    max_drawdown_pct: Optional[Decimal] = Field(
        None, gt=0, lt=1, description="Maximum drawdown from peak"
    )

    @field_validator("max_daily_loss_pct", "max_drawdown_pct")
    def validate_percentages(cls, v):
        """Validate percentages are between 0 and 1."""
        if v is not None and (v <= 0 or v >= 1):
            raise ValueError("Percentage values must be between 0 and 1")
        return v


class RiskMetrics(BaseModel):
    """Current portfolio risk metrics."""

    portfolio_value: Decimal = Field(..., description="Current portfolio value")
    cash: Decimal = Field(..., description="Available cash")
    equity: Decimal = Field(..., description="Equity value (portfolio - cash)")
    leverage: Decimal = Field(..., description="Current leverage ratio")

    # Daily metrics
    daily_pnl: Decimal = Field(default=Decimal("0"), description="Daily P&L")
    daily_pnl_pct: Decimal = Field(
        default=Decimal("0"), description="Daily P&L percentage"
    )

    # Drawdown metrics
    peak_value: Decimal = Field(..., description="Historical peak portfolio value")
    current_drawdown: Decimal = Field(
        default=Decimal("0"), description="Current drawdown from peak"
    )
    current_drawdown_pct: Decimal = Field(
        default=Decimal("0"), description="Current drawdown percentage"
    )

    # Position metrics
    largest_position_value: Decimal = Field(
        default=Decimal("0"), description="Largest single position value"
    )
    largest_position_pct: Decimal = Field(
        default=Decimal("0"), description="Largest position as % of portfolio"
    )

    def update_drawdown(self):
        """Update drawdown metrics."""
        if self.portfolio_value > self.peak_value:
            self.peak_value = self.portfolio_value
            self.current_drawdown = Decimal("0")
            self.current_drawdown_pct = Decimal("0")
        else:
            self.current_drawdown = self.peak_value - self.portfolio_value
            self.current_drawdown_pct = (
                self.current_drawdown / self.peak_value
                if self.peak_value > 0
                else Decimal("0")
            )


class RiskManager:
    """Portfolio risk management system."""

    def __init__(
        self,
        position_limits: Optional[PositionLimits] = None,
        drawdown_limits: Optional[DrawdownLimits] = None,
    ):
        """Initialize risk manager."""
        self.position_limits = position_limits or PositionLimits()
        self.drawdown_limits = drawdown_limits or DrawdownLimits()

        # Risk state
        self.alerts: List[RiskAlert] = []
        self.risk_metrics: Optional[RiskMetrics] = None
        self.daily_start_value: Optional[Decimal] = None

        logger.info(
            "Risk manager initialized",
            position_limits=self.position_limits.dict(),
            drawdown_limits=self.drawdown_limits.dict(),
        )

    def update_metrics(
        self,
        portfolio_value: Decimal,
        cash: Decimal,
        positions: Dict[str, Dict[str, Any]],
    ) -> RiskMetrics:
        """Update risk metrics and check limits."""
        equity = portfolio_value - cash
        leverage = equity / portfolio_value if portfolio_value > 0 else Decimal("0")

        # Initialize daily tracking
        if self.daily_start_value is None:
            self.daily_start_value = portfolio_value

        # Calculate daily P&L
        daily_pnl = portfolio_value - self.daily_start_value
        daily_pnl_pct = (
            daily_pnl / self.daily_start_value
            if self.daily_start_value > 0
            else Decimal("0")
        )

        # Calculate position metrics
        largest_position_value = Decimal("0")
        largest_position_pct = Decimal("0")

        for symbol, position in positions.items():
            position_value = Decimal(str(abs(position.get("value", 0))))
            if position_value > largest_position_value:
                largest_position_value = position_value
                largest_position_pct = (
                    position_value / portfolio_value
                    if portfolio_value > 0
                    else Decimal("0")
                )

        # Create or update metrics
        if self.risk_metrics is None:
            peak_value = portfolio_value
        else:
            peak_value = max(self.risk_metrics.peak_value, portfolio_value)

        self.risk_metrics = RiskMetrics(
            portfolio_value=portfolio_value,
            cash=cash,
            equity=equity,
            leverage=leverage,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            peak_value=peak_value,
            largest_position_value=largest_position_value,
            largest_position_pct=largest_position_pct,
        )

        # Update drawdown calculations
        self.risk_metrics.update_drawdown()

        # Check risk limits
        self._check_risk_limits()

        return self.risk_metrics

    def validate_trade(
        self,
        symbol: str,
        action: str,
        size: int,
        price: float,
        current_position: int = 0,
    ) -> bool:
        """Validate trade against risk limits."""
        if not self.risk_metrics:
            logger.warning("No risk metrics available for trade validation")
            return True

        # Calculate new position after trade
        if action == "buy":
            new_position = current_position + size
        elif action == "sell":
            new_position = current_position - size
        else:
            return True

        new_position_value = abs(new_position) * Decimal(str(price))

        # Check position size limits
        if self.position_limits.max_position_size:
            if abs(new_position) > self.position_limits.max_position_size:
                self._create_alert(
                    RiskLevel.HIGH,
                    f"Trade rejected: Position size {abs(new_position)} exceeds limit {self.position_limits.max_position_size}",
                    "position_size",
                    abs(new_position),
                    self.position_limits.max_position_size,
                )
                return False

        # Check position value limits
        if self.position_limits.max_position_value:
            if new_position_value > self.position_limits.max_position_value:
                self._create_alert(
                    RiskLevel.HIGH,
                    f"Trade rejected: Position value ${new_position_value} exceeds limit ${self.position_limits.max_position_value}",
                    "position_value",
                    float(new_position_value),
                    float(self.position_limits.max_position_value),
                )
                return False

        # Check portfolio concentration limits
        if self.position_limits.max_portfolio_concentration:
            new_concentration = new_position_value / self.risk_metrics.portfolio_value
            if new_concentration > self.position_limits.max_portfolio_concentration:
                self._create_alert(
                    RiskLevel.HIGH,
                    f"Trade rejected: Position concentration {new_concentration:.2%} exceeds limit {self.position_limits.max_portfolio_concentration:.2%}",
                    "portfolio_concentration",
                    float(new_concentration),
                    float(self.position_limits.max_portfolio_concentration),
                )
                return False

        return True

    def _check_risk_limits(self):
        """Check current metrics against risk limits."""
        if not self.risk_metrics:
            return

        # Check daily loss limits
        if self.drawdown_limits.max_daily_loss:
            if abs(self.risk_metrics.daily_pnl) > self.drawdown_limits.max_daily_loss:
                self._create_alert(
                    RiskLevel.CRITICAL,
                    f"Daily loss ${abs(self.risk_metrics.daily_pnl)} exceeds limit ${self.drawdown_limits.max_daily_loss}",
                    "daily_loss",
                    float(abs(self.risk_metrics.daily_pnl)),
                    float(self.drawdown_limits.max_daily_loss),
                )

        if self.drawdown_limits.max_daily_loss_pct:
            if (
                abs(self.risk_metrics.daily_pnl_pct)
                > self.drawdown_limits.max_daily_loss_pct
            ):
                self._create_alert(
                    RiskLevel.CRITICAL,
                    f"Daily loss {abs(self.risk_metrics.daily_pnl_pct):.2%} exceeds limit {self.drawdown_limits.max_daily_loss_pct:.2%}",
                    "daily_loss_pct",
                    float(abs(self.risk_metrics.daily_pnl_pct)),
                    float(self.drawdown_limits.max_daily_loss_pct),
                )

        # Check drawdown limits
        if self.drawdown_limits.max_drawdown_pct:
            if (
                self.risk_metrics.current_drawdown_pct
                > self.drawdown_limits.max_drawdown_pct
            ):
                self._create_alert(
                    RiskLevel.CRITICAL,
                    f"Drawdown {self.risk_metrics.current_drawdown_pct:.2%} exceeds limit {self.drawdown_limits.max_drawdown_pct:.2%}",
                    "drawdown_pct",
                    float(self.risk_metrics.current_drawdown_pct),
                    float(self.drawdown_limits.max_drawdown_pct),
                )

        # Check portfolio concentration
        if self.position_limits.max_portfolio_concentration:
            if (
                self.risk_metrics.largest_position_pct
                > self.position_limits.max_portfolio_concentration
            ):
                self._create_alert(
                    RiskLevel.MEDIUM,
                    f"Largest position {self.risk_metrics.largest_position_pct:.2%} exceeds concentration limit {self.position_limits.max_portfolio_concentration:.2%}",
                    "portfolio_concentration",
                    float(self.risk_metrics.largest_position_pct),
                    float(self.position_limits.max_portfolio_concentration),
                )

    def _create_alert(
        self,
        level: RiskLevel,
        message: str,
        metric: str,
        value: float,
        threshold: float,
    ):
        """Create and log risk alert."""
        alert = RiskAlert(
            level=level,
            message=message,
            metric=metric,
            value=value,
            threshold=threshold,
        )

        self.alerts.append(alert)

        logger.warning(
            "Risk alert generated",
            level=level,
            metric=metric,
            message=message,
            value=value,
            threshold=threshold,
        )

    def get_active_alerts(self, level: Optional[RiskLevel] = None) -> List[RiskAlert]:
        """Get active risk alerts, optionally filtered by level."""
        if level:
            return [alert for alert in self.alerts if alert.level == level]
        return self.alerts.copy()

    def clear_alerts(self):
        """Clear all risk alerts."""
        self.alerts.clear()
        logger.info("Risk alerts cleared")

    def reset_daily_tracking(self):
        """Reset daily tracking metrics (call at start of each trading day)."""
        if self.risk_metrics:
            self.daily_start_value = self.risk_metrics.portfolio_value
            logger.info("Daily risk tracking reset", start_value=self.daily_start_value)

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        return {
            "metrics": self.risk_metrics.dict() if self.risk_metrics else None,
            "limits": {
                "position": self.position_limits.dict(),
                "drawdown": self.drawdown_limits.dict(),
            },
            "alerts": {
                "total": len(self.alerts),
                "critical": len(
                    [a for a in self.alerts if a.level == RiskLevel.CRITICAL]
                ),
                "high": len([a for a in self.alerts if a.level == RiskLevel.HIGH]),
                "medium": len([a for a in self.alerts if a.level == RiskLevel.MEDIUM]),
                "low": len([a for a in self.alerts if a.level == RiskLevel.LOW]),
            },
        }
