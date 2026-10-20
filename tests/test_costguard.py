import datetime as dt
import tempfile
import unittest
from pathlib import Path

from costguard import (Budget, BudgetExceeded, BudgetGuard, CostLedger, LoopGuard, LoopStop,
                       Usage, cache_hit_rate, cascade, cost_usd, from_anthropic, from_openai,
                       truncate_tool_result, usd_to_jpy, worst_case_usd)

UTC = dt.timezone.utc


class PricingTest(unittest.TestCase):
    def test_cost(self):
        # Sonnet 5.5: 入力 $2、出力 $10 / MTok
        self.assertAlmostEqual(cost_usd("claude-sonnet-5-5", Usage(1_000_000, 100_000)), 3.0)

    def test_cache_cheaper(self):
        plain = cost_usd("claude-sonnet-5-5", Usage(input=100_000))
        cached = cost_usd("claude-sonnet-5-5", Usage(cache_read=100_000))
        self.assertAlmostEqual(cached / plain, 0.05)

    def test_batch_discount(self):
        u = Usage(1_000_000, 0)
        self.assertAlmostEqual(cost_usd("claude-opus-5-5", u, discount=0.5), 2.0)

    def test_unknown_model(self):
        with self.assertRaises(KeyError):
            cost_usd("no-such-model", Usage(1))

    def test_from_anthropic(self):
        u = from_anthropic({"input_tokens": 50, "output_tokens": 10,
                            "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 0})
        self.assertEqual(u, Usage(50, 10, 2000, 0))

    def test_from_openai_subtracts_cached(self):
        u = from_openai({"input_tokens": 3000, "output_tokens": 20,
                         "input_tokens_details": {"cached_tokens": 2048}})
        self.assertEqual(u, Usage(952, 20, 0, 2048))

    def test_worst_case(self):
        self.assertAlmostEqual(worst_case_usd("claude-haiku-5-5", 10_000, 1_000), 0.0015)


class LedgerGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = CostLedger(Path(self.tmp.name) / "cost.jsonl")
        self.now = dt.datetime(2026, 10, 20, 12, tzinfo=UTC)

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_and_spent(self):
        self.ledger.record(task="t1", model="claude-sonnet-5-5", usage=Usage(1_000_000, 0), now=self.now)
        self.ledger.record(task="t2", model="claude-sonnet-5-5", usage=Usage(0, 100_000), now=self.now)
        self.assertAlmostEqual(self.ledger.spent(), 3.0)
        self.assertAlmostEqual(self.ledger.spent(task="t1"), 2.0)
        s = self.ledger.summary("task")
        self.assertEqual(s["t1"]["calls"], 1)

    def test_since(self):
        old = self.now - dt.timedelta(days=40)
        self.ledger.record(task="t", model="claude-sonnet-5-5", usage=Usage(1_000_000, 0), now=old)
        self.ledger.record(task="t", model="claude-sonnet-5-5", usage=Usage(1_000_000, 0), now=self.now)
        self.assertAlmostEqual(self.ledger.spent(since=self.now - dt.timedelta(days=1)), 2.0)

    def test_guard_blocks_task(self):
        g = BudgetGuard(self.ledger, Budget(per_task=0.05), clock=lambda: self.now)
        self.ledger.record(task="t", model="claude-sonnet-5-5", usage=Usage(20_000, 0), now=self.now)  # $0.04
        with self.assertRaises(BudgetExceeded):
            g.check(task="t", model="claude-sonnet-5-5", input_tokens=5_000, max_tokens=1_000)  # +$0.02
        # 別タスクなら通る
        self.assertAlmostEqual(
            g.check(task="u", model="claude-sonnet-5-5", input_tokens=5_000, max_tokens=1_000), 0.02)

    def test_guard_day_ignores_yesterday(self):
        g = BudgetGuard(self.ledger, Budget(per_day=1.0), clock=lambda: self.now)
        self.ledger.record(task="x", model="claude-sonnet-5-5", usage=Usage(1_000_000, 0),
                           now=self.now - dt.timedelta(days=1))
        g.check(task="y", model="claude-sonnet-5-5", input_tokens=100_000, max_tokens=1_000)

    def test_guard_per_call(self):
        g = BudgetGuard(self.ledger, Budget(per_call=0.10), clock=lambda: self.now)
        with self.assertRaises(BudgetExceeded):
            g.check(task="t", model="claude-opus-5-5", input_tokens=10_000, max_tokens=64_000)


class LoopTest(unittest.TestCase):
    def test_max_steps(self):
        g = LoopGuard(max_steps=3)
        for _ in range(3):
            g.step()
        with self.assertRaises(LoopStop):
            g.step()

    def test_same_call(self):
        g = LoopGuard(max_same_call=2)
        g.step("search", {"q": "a"})
        g.step("search", {"q": "a"})
        g.step("search", {"q": "b"})
        with self.assertRaises(LoopStop):
            g.step("search", {"q": "a"})

    def test_no_progress(self):
        g = LoopGuard(max_no_progress=2)
        g.step(state=1)
        g.step(state=2)
        g.step(state=2)
        with self.assertRaises(LoopStop):
            g.step(state=2)


class TuneTest(unittest.TestCase):
    def test_hit_rate(self):
        self.assertAlmostEqual(cache_hit_rate(Usage(input=100, cache_read=900)), 0.9)
        self.assertEqual(cache_hit_rate(Usage()), 0.0)

    def test_truncate(self):
        t = "a" * 10_000
        out = truncate_tool_result(t, max_chars=4000, head=100, tail=50)
        self.assertTrue(out.startswith("a" * 100))
        self.assertIn("9850文字省略", out)
        self.assertEqual(truncate_tool_result("short"), "short")

    def test_cascade(self):
        calls = []

        def call(model, prompt):
            calls.append(model)
            return ("OK" if model == "big" else "??"), Usage(10, 5)

        text, model, total, tried = cascade("q", call, ["small", "big"], lambda t: t == "OK")
        self.assertEqual((text, model), ("OK", "big"))
        self.assertEqual(total, Usage(20, 10))
        self.assertEqual(tried, [("small", False), ("big", True)])

    def test_jpy(self):
        self.assertEqual(usd_to_jpy(10, 150.4), 1504)


if __name__ == "__main__":
    unittest.main()
