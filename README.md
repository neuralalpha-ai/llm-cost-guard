# llm-cost-guard

Small, dependency-free Python parts for keeping LLM / AI-agent API bills **readable, stoppable and lower**.
Standard library only. 19 unit tests. MIT.

| Module | What it does |
|---|---|
| `costguard/pricing.py` | Dated price table, `Usage` normalized across Anthropic / OpenAI usage fields, `cost_usd`, worst-case estimate |
| `costguard/ledger.py` | One-line-per-request JSONL cost ledger with per task / model / day summaries |
| `costguard/guard.py` | Budget guard that stops a call **before** it is made (per call / task / day / month) |
| `costguard/loop.py` | Agent-loop guard: max steps, repeated identical tool calls, no-progress detection |
| `costguard/tune.py` | Cache hit rate, tool-result truncation, cheap-first model cascade, USD→JPY |
| `simulate_loop.py` | Shows how input tokens grow with loop turns, with and without prompt caching (no API calls) |

```bash
python -m unittest discover -s tests -t .
python simulate_loop.py
```

**Prices change.** `pricing.py` holds prices copied from official pricing pages on the date in `AS_OF` (2026-10-20). Check the official pages and update the table before relying on it. Model ID strings are illustrative; use the IDs from each provider's docs. The parts are tested with unit tests only; calls to real APIs are not included.

## 日本語

AIエージェント・LLM の API 費用を「読める・止められる・下げられる」ようにする、標準ライブラリだけの小さな部品集です。
解説書：『AIエージェントのコスト管理実践ガイド ― 請求を読み、止め、下げるPython実装』（Zenn）
https://zenn.dev/neuralalpha/books/agent-cost-guide

料金は変わります。`pricing.py` の単価は `AS_OF`（2026-10-20）時点の公式ページから転記したものです。使う前に公式ページで確認してください。

Free checklist: https://neuralalpha.gumroad.com/l/agent-ops-preflight?utm_source=github&utm_medium=readme_costguard
