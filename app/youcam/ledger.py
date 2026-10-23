"""Unit ledger and budget guard.

Every live call is authorised *before* it is sent:
  * the account must keep `reserve` units untouched (checked against the real
    balance from GET /s2s/v1.0/client/credit when available, else our own count);
  * one visitor (IP) may spend at most `per_client_daily` units per day.
Spends are appended to a JSONL file so the numbers survive restarts.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .errors import BudgetExceeded


@dataclass
class Spend:
    ts: float
    feature: str
    units: int
    task_id: str
    client: str
    mode: str


class UnitLedger:
    def __init__(self, path: Path, *, mode: str, budget: int, reserve: int, per_client_daily: int):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.budget = budget
        self.reserve = reserve
        self.per_client_daily = per_client_daily
        self._lock = threading.Lock()
        self.live_balance: float | None = None   # last value read from the credit API
        self.live_balance_at = 0.0
        self.spends: list[Spend] = []
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("mode") == mode:
                    self.spends.append(Spend(**row))

    # ------------------------------------------------------------------ queries
    @property
    def spent(self) -> int:
        return sum(s.units for s in self.spends)

    def spent_by(self, client: str, since: float | None = None) -> int:
        since = since if since is not None else time.time() - 86400
        return sum(s.units for s in self.spends if s.client == client and s.ts >= since)

    def remaining(self) -> float:
        if self.live_balance is not None:
            return self.live_balance
        return self.budget - self.spent

    def by_feature(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self.spends:
            out[s.feature] = out.get(s.feature, 0) + s.units
        return out

    # ------------------------------------------------------------------ guard
    def authorize(self, units: int, client: str) -> None:
        with self._lock:
            if self.remaining() - units < self.reserve:
                raise BudgetExceeded(
                    f"needs {units} units but only {self.remaining():.0f} left and {self.reserve} are reserved")
            if self.spent_by(client) + units > self.per_client_daily:
                raise BudgetExceeded(f"daily limit of {self.per_client_daily} units per visitor reached")

    def record(self, feature: str, units: int, task_id: str, client: str) -> Spend:
        s = Spend(time.time(), feature, int(units), task_id, client, self.mode)
        with self._lock:
            self.spends.append(s)
            if self.live_balance is not None:
                self.live_balance -= units
            with self.path.open("a") as fh:
                fh.write(json.dumps(s.__dict__) + "\n")
        return s

    def set_live_balance(self, units: float) -> None:
        self.live_balance = float(units)
        self.live_balance_at = time.time()

    def summary(self) -> dict:
        return {"mode": self.mode, "spent": self.spent, "remaining": round(self.remaining(), 2),
                "reserve": self.reserve, "budget": self.budget, "per_client_daily": self.per_client_daily,
                "balance_source": "youcam-credit-api" if self.live_balance is not None else "local-ledger",
                "by_feature": self.by_feature(), "calls": len(self.spends)}
