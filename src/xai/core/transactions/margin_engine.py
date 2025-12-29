"""
Margin trading infrastructure supporting isolated and cross-margin accounts.

Implements:
- MarginAccount and Position primitives
- Leverage validation per asset with configurable risk parameters
- Health-factor based liquidation for cross and isolated positions
- Realized/unrealized PnL tracking with position averaging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable

DecimalLike = Decimal | float | str | int

def to_decimal(value: DecimalLike) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

class MarginException(Exception):
    """Raised when margin operations violate risk constraints."""

@dataclass
class AssetRiskParams:
    max_leverage: Decimal = Decimal("5")
    initial_margin: Decimal = Decimal("0.2")  # 20%
    maintenance_margin: Decimal = Decimal("0.1")  # 10%

@dataclass
class Position:
    asset: str
    size: Decimal
    entry_price: Decimal
    isolated: bool
    leverage: Decimal
    margin: Decimal
    realized_pnl: Decimal = Decimal("0")

    def notional(self, mark_price: Decimal) -> Decimal:
        return abs(self.size) * mark_price

    def unrealized_pnl(self, mark_price: Decimal) -> Decimal:
        return (mark_price - self.entry_price) * self.size

    def update_on_fill(self, additional_size: Decimal, fill_price: Decimal) -> None:
        if self.size == Decimal("0"):
            self.entry_price = fill_price
            self.size = additional_size
            return
        new_size = self.size + additional_size
        if new_size == Decimal("0"):
            self.size = Decimal("0")
            self.entry_price = Decimal("0")
            return
        weighted_price = (
            self.entry_price * self.size + fill_price * additional_size
        ) / new_size
        self.entry_price = weighted_price.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        self.size = new_size

@dataclass
class MarginAccount:
    account_id: str
    mode: str = "cross"
    collateral: Decimal = Decimal("0")
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: Decimal = Decimal("0")

    def equity(self, mark_prices: dict[str, Decimal]) -> Decimal:
        equity = self.collateral + self.realized_pnl
        for asset, position in self.positions.items():
            price = mark_prices.get(asset)
            if price is None:
                continue
            equity += position.unrealized_pnl(price)
        return equity

class MarginEngine:
    def __init__(
        self,
        price_oracle: Callable[[str], Decimal],
        asset_risk: dict[str, AssetRiskParams] | None = None,
        default_risk: AssetRiskParams | None = None,
        liquidation_penalty: DecimalLike = Decimal("0.005"),
    ):
        self.price_oracle = price_oracle
        self.asset_risk = asset_risk or {}
        self.default_risk = default_risk or AssetRiskParams()
        self.accounts: dict[str, MarginAccount] = {}
        self.liquidation_penalty = to_decimal(liquidation_penalty)

    def _get_account(self, account_id: str) -> MarginAccount:
        if account_id not in self.accounts:
            self.accounts[account_id] = MarginAccount(account_id=account_id)
        return self.accounts[account_id]

    def get_positions(self, account_id: str) -> dict[str, Position]:
        account = self.accounts.get(account_id)
        if not account:
            return {}
        return account.positions

    def _risk(self, asset: str) -> AssetRiskParams:
        return self.asset_risk.get(asset.upper(), self.default_risk)

    def deposit(self, account_id: str, amount: DecimalLike) -> None:
        account = self._get_account(account_id)
        account.collateral += to_decimal(amount)

    def withdraw(self, account_id: str, amount: DecimalLike) -> None:
        account = self._get_account(account_id)
        amount_dec = to_decimal(amount)
        if amount_dec > account.collateral:
            raise MarginException("Insufficient collateral")
        mark_prices = self._mark_prices(account.positions.keys())
        if account.equity(mark_prices) - amount_dec < Decimal("0"):
            raise MarginException("Withdrawal would make equity negative")
        account.collateral -= amount_dec

    def open_position(
        self,
        account_id: str,
        asset: str,
        size: DecimalLike,
        *,
        isolated: bool = False,
        leverage: DecimalLike | None = None,
        mark_price: DecimalLike | None = None,
    ) -> Position:
        account = self._get_account(account_id)
        risk = self._risk(asset)
        mark = to_decimal(mark_price) if mark_price is not None else self.price_oracle(asset)
        size_dec = to_decimal(size)
        direction = "long" if size_dec > 0 else "short"
        leverage_dec = to_decimal(leverage) if leverage is not None else risk.max_leverage
        if leverage_dec <= 0 or leverage_dec > risk.max_leverage:
            raise MarginException("Invalid leverage selection")
        notional = abs(size_dec) * mark
        required_margin = (notional / leverage_dec).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        if account.collateral < required_margin and not isolated:
            raise MarginException("Insufficient collateral for cross-margin position")
        if isolated and required_margin > account.collateral:
            raise MarginException("Insufficient collateral for isolated position")

        existing = account.positions.get(asset)
        if existing:
            existing.update_on_fill(size_dec, mark)
            existing.margin += required_margin
            existing.leverage = leverage_dec
        else:
            account.positions[asset] = Position(
                asset=asset,
                size=size_dec,
                entry_price=mark,
                isolated=isolated,
                leverage=leverage_dec,
                margin=required_margin,
            )
        if not isolated:
            account.collateral -= required_margin
        else:
            account.positions[asset].margin = required_margin
        return account.positions[asset]

    def close_position(
        self,
        account_id: str,
        asset: str,
        size: DecimalLike | None = None,
        mark_price: DecimalLike | None = None,
    ) -> dict[str, Decimal]:
        account = self._get_account(account_id)
        position = account.positions.get(asset)
        if not position:
            raise MarginException("No position for asset")
        mark = to_decimal(mark_price) if mark_price is not None else self.price_oracle(asset)
        close_size = position.size if size is None else to_decimal(size)
        if close_size == Decimal("0"):
            raise MarginException("Close size cannot be zero")
        if abs(close_size) > abs(position.size):
            raise MarginException("Cannot close more than open size")
        pnl = (mark - position.entry_price) * close_size
        position.realized_pnl += pnl
        account.realized_pnl += pnl
        position.size -= close_size
        if position.size == Decimal("0"):
            released_margin = position.margin
            if not position.isolated:
                account.collateral += released_margin
            del account.positions[asset]
        else:
            position.margin *= abs(position.size) / (abs(position.size) + abs(close_size))
        return {"realized_pnl": pnl, "remaining_size": position.size}

    def account_overview(self, account_id: str) -> dict[str, Decimal]:
        account = self._get_account(account_id)
        mark_prices = self._mark_prices(account.positions.keys())
        equity = account.equity(mark_prices)
        maintenance = self._maintenance_requirement(account, mark_prices)
        hf = equity / maintenance if maintenance > 0 else Decimal("infinity")
        return {
            "collateral": account.collateral,
            "equity": equity,
            "maintenance_requirement": maintenance,
            "health_factor": hf,
        }

    def perform_liquidations(self) -> list[str]:
        liquidated: list[str] = []
        for account_id, account in list(self.accounts.items()):
            mark_prices = self._mark_prices(account.positions.keys())
            equity = account.equity(mark_prices)
            maintenance = self._maintenance_requirement(account, mark_prices)
            if maintenance == 0 or equity >= maintenance:
                continue
            for asset, position in list(account.positions.items()):
                mark = mark_prices[asset]
                penalty = position.notional(mark) * self.liquidation_penalty
                position_realized = position.unrealized_pnl(mark) - penalty
                account.realized_pnl += position_realized
                if not position.isolated:
                    account.collateral += position.margin
                del account.positions[asset]
            liquidated.append(account_id)
        return liquidated

    def _mark_prices(self, assets: list[str] | dict[str, Position]) -> dict[str, Decimal]:
        marks: dict[str, Decimal] = {}
        keys = assets.keys() if isinstance(assets, dict) else assets
        for asset in keys:
            marks[asset] = self.price_oracle(asset)
        return marks

    def _maintenance_requirement(self, account: MarginAccount, marks: dict[str, Decimal]) -> Decimal:
        requirement = Decimal("0")
        for asset, position in account.positions.items():
            risk = self._risk(asset)
            mark = marks.get(asset)
            if mark is None:
                continue
            requirement += position.notional(mark) * risk.maintenance_margin
        return requirement
