"""エージェントループの暴走を止めるガード。"""
import hashlib
import json
from collections import Counter


class LoopStop(RuntimeError):
    pass


def call_signature(tool, args):
    """同じツールを同じ引数で呼んだかを判定するためのハッシュ。"""
    raw = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class LoopGuard:
    def __init__(self, max_steps=20, max_same_call=3, max_no_progress=5):
        self.max_steps = max_steps
        self.max_same_call = max_same_call
        self.max_no_progress = max_no_progress
        self.steps = 0
        self.seen = Counter()
        self.no_progress = 0
        self._last_state = None

    def step(self, tool=None, args=None, state=None):
        """ループ1周ごとに呼ぶ。state は「進んだか」を表す値（例：完了したTODO数）。"""
        self.steps += 1
        if self.steps > self.max_steps:
            raise LoopStop(f"反復が上限 {self.max_steps} 回を超えた")
        if tool is not None:
            sig = call_signature(tool, args or {})
            self.seen[sig] += 1
            if self.seen[sig] > self.max_same_call:
                raise LoopStop(f"同じ呼び出し {tool} が {self.seen[sig]} 回目")
        if state is not None:
            if state == self._last_state:
                self.no_progress += 1
                if self.no_progress >= self.max_no_progress:
                    raise LoopStop(f"{self.no_progress} 周続けて進捗なし")
            else:
                self.no_progress = 0
                self._last_state = state
