"""呼び出す前に止める予算ガード。"""
import datetime as dt
from dataclasses import dataclass
from typing import Optional

from .pricing import worst_case_usd


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class Budget:
    per_call: Optional[float] = None   # 1回の呼び出しの最悪ケース上限（USD）
    per_task: Optional[float] = None   # 1タスク（1回のエージェント実行）
    per_day: Optional[float] = None    # UTC の1日
    per_month: Optional[float] = None  # UTC の1か月


class BudgetGuard:
    def __init__(self, ledger, budget, clock=None):
        self.ledger = ledger
        self.budget = budget
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))

    def check(self, *, task, model, input_tokens, max_tokens):
        """呼び出し前に実行。超えるなら BudgetExceeded。見積もり USD を返す。"""
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
                    f"{name}: 使用済み ${spent:.4f} + 見積もり ${est:.4f} > 上限 ${limit:.4f}")
        return est
