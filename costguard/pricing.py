"""モデル単価表と、usage から費用を計算する関数。

単価は USD / 100万トークン。AS_OF の日付時点の公式料金ページから転記したもの。
料金は変わるので、使う前に必ず公式ページで確認し、この表を更新すること。
"""
from dataclasses import dataclass

AS_OF = "2026-10-20"


@dataclass(frozen=True)
class Price:
    input: float           # 通常の入力
    output: float          # 出力（思考トークンを含む）
    cache_write: float     # キャッシュ書き込み（5分TTL相当）
    cache_read: float      # キャッシュ読み取り


# モデルIDは各社の表記に合わせて書き換えること（ここでは説明用の名前）。
PRICES = {
    "claude-opus-5-5": Price(4.00, 20.00, 5.00, 0.20),
    "claude-sonnet-5-5": Price(2.00, 10.00, 2.50, 0.10),
    "claude-haiku-5-5": Price(0.10, 0.50, 0.125, 0.01),  # プロンプト10万トークン以下
    "gpt-6.1-sol": Price(2.00, 10.00, 2.50, 0.10),
    "gpt-6-luna": Price(0.10, 0.50, 0.125, 0.01),
}


@dataclass(frozen=True)
class Usage:
    """プロバイダの違いをならした使用量。input は「キャッシュ以外の入力」。"""
    input: int = 0
    output: int = 0
    cache_write: int = 0
    cache_read: int = 0

    def __add__(self, other):
        return Usage(self.input + other.input, self.output + other.output,
                     self.cache_write + other.cache_write,
                     self.cache_read + other.cache_read)


def from_anthropic(u):
    """Anthropic の usage（dict）を Usage に。input_tokens はキャッシュ分を含まない。"""
    return Usage(
        input=u.get("input_tokens", 0) or 0,
        output=u.get("output_tokens", 0) or 0,
        cache_write=u.get("cache_creation_input_tokens", 0) or 0,
        cache_read=u.get("cache_read_input_tokens", 0) or 0,
    )


def from_openai(u):
    """OpenAI の usage（dict）を Usage に。input_tokens はキャッシュ分を含むので引く。"""
    total_in = u.get("input_tokens", u.get("prompt_tokens", 0)) or 0
    details = u.get("input_tokens_details") or u.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens", 0) or 0
    written = details.get("cache_write_tokens", 0) or 0
    return Usage(
        input=max(total_in - cached - written, 0),
        output=u.get("output_tokens", u.get("completion_tokens", 0)) or 0,
        cache_write=written,
        cache_read=cached,
    )


def cost_usd(model, usage, prices=PRICES, discount=1.0):
    """usage の費用（USD）。discount はバッチなら 0.5 のように掛ける。"""
    if model not in prices:
        raise KeyError(f"単価表にないモデル: {model}（推測で計算しない）")
    p = prices[model]
    total = (usage.input * p.input + usage.output * p.output
             + usage.cache_write * p.cache_write
             + usage.cache_read * p.cache_read) / 1_000_000
    return round(total * discount, 6)


def worst_case_usd(model, input_tokens, max_tokens, prices=PRICES):
    """呼ぶ前の見積もり：入力は全部キャッシュなし、出力は max_tokens まで出たと仮定。"""
    return cost_usd(model, Usage(input=input_tokens, output=max_tokens), prices)
