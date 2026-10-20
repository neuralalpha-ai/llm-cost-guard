"""Guard that stops runaway agent loops."""
import hashlib
import json
from collections import Counter


class LoopStop(RuntimeError):
    pass


def call_signature(tool, args):
    """Hash used to detect a call to the same tool with the same arguments."""
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
        """Call once per loop iteration. state is a value that shows progress (e.g. number of finished TODOs)."""
        self.steps += 1
        if self.steps > self.max_steps:
            raise LoopStop(f"steps exceeded the limit of {self.max_steps}")
        if tool is not None:
            sig = call_signature(tool, args or {})
            self.seen[sig] += 1
            if self.seen[sig] > self.max_same_call:
                raise LoopStop(f"same call {tool} repeated {self.seen[sig]} times")
        if state is not None:
            if state == self._last_state:
                self.no_progress += 1
                if self.no_progress >= self.max_no_progress:
                    raise LoopStop(f"no progress for {self.no_progress} consecutive steps")
            else:
                self.no_progress = 0
                self._last_state = state
