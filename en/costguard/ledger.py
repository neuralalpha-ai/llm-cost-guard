"""Cost ledger with one line per request (JSON Lines)."""
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

from .pricing import Usage, cost_usd


def _now():
    return dt.datetime.now(dt.timezone.utc)


class CostLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, *, task, model, usage, discount=1.0, now=None, **meta):
        """Always call right after an API call. Record failed calls too if they returned usage."""
        row = {
            "ts": (now or _now()).isoformat(timespec="seconds"),
            "task": task,
            "model": model,
            "in": usage.input,
            "out": usage.output,
            "cw": usage.cache_write,
            "cr": usage.cache_read,
            "usd": cost_usd(model, usage, discount=discount),
            **meta,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def rows(self):
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def spent(self, *, task=None, since=None):
        """Total USD, for one task if task is given, and from since (a datetime) onward."""
        total = 0.0
        for r in self.rows():
            if task is not None and r["task"] != task:
                continue
            if since is not None and dt.datetime.fromisoformat(r["ts"]) < since:
                continue
            total += r["usd"]
        return round(total, 6)

    def summary(self, key="model"):
        """Calls, tokens, and USD per key (model / task / date "day")."""
        out = defaultdict(lambda: {"calls": 0, "usage": Usage(), "usd": 0.0})
        for r in self.rows():
            k = r["ts"][:10] if key == "day" else r.get(key)
            s = out[k]
            s["calls"] += 1
            s["usage"] = s["usage"] + Usage(r["in"], r["out"], r["cw"], r["cr"])
            s["usd"] = round(s["usd"] + r["usd"], 6)
        return dict(out)
