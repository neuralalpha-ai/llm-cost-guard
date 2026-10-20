"""A budget guard that stops calls before they are made."""
import datetime as dt
from dataclasses import dataclass
from typing import Optional

from .pricing import worst_case_usd


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class Budget:
    per_call: Optional[float] = None   # worst-case limit for one call (USD)
    per_task: Optional[float] = None   # one task (one agent run)
    per_day: Optional[float] = None    # one UTC day
    per_month: Optional[float] = None  # one UTC month


class BudgetGuard:
    def __init__(self, ledger, budget, clock=None):
        self.ledger = ledger
        self.budget = budget
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))

    def check(self, *, task, model, input_tokens, max_tokens):
        """Run before the call. Raises BudgetExceeded if over. Returns the estimate in USD."""
        est = worst_case_usd(model, input_tokens, max_tokens)
        b = self.budget
        now = self.clock()
        day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month0 = day0.replace(day=1)
        checks = [
            ("per_call", b.per_call, 0.0),
            ("per_task", b.per_task, self.ledger.spent(task=task)),
            ("per_day", b.per_day, self.ledger.spent(since=day0)),
            ("per_month", b.per_month, self.ledger.spent(since=month0)),
        ]
        for name, limit, spent in checks:
            if limit is not None and spent + est > limit:
                raise BudgetExceeded(
                    f"{name}: spent ${spent:.4f} + estimate ${est:.4f} > limit ${limit:.4f}")
        return est
