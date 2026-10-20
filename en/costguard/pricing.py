"""Model price table and functions that compute cost from usage.

Prices are USD per million tokens, copied from official pricing pages as of AS_OF.
Prices change: check the official pages and update this table before relying on it.
"""
from dataclasses import dataclass

AS_OF = "2026-10-20"


@dataclass(frozen=True)
class Price:
    input: float           # normal input
    output: float          # output (includes thinking tokens)
    cache_write: float     # cache write (5-minute TTL rate)
    cache_read: float      # cache read


# Change the model IDs to match each provider's naming (these are illustrative names).
PRICES = {
    "claude-opus-5-5": Price(4.00, 20.00, 5.00, 0.20),
    "claude-sonnet-5-5": Price(2.00, 10.00, 2.50, 0.10),
    "claude-haiku-5-5": Price(0.10, 0.50, 0.125, 0.01),  # prompts of 100k tokens or less
    "gpt-6.1-sol": Price(2.00, 10.00, 2.50, 0.10),
    "gpt-6-luna": Price(0.10, 0.50, 0.125, 0.01),
}


@dataclass(frozen=True)
class Usage:
    """Usage with provider differences smoothed out. input is "non-cached input"."""
    input: int = 0
    output: int = 0
    cache_write: int = 0
    cache_read: int = 0

    def __add__(self, other):
        return Usage(self.input + other.input, self.output + other.output,
                     self.cache_write + other.cache_write,
                     self.cache_read + other.cache_read)


def from_anthropic(u):
    """Anthropic usage (dict) to Usage. input_tokens does not include cached tokens."""
    return Usage(
        input=u.get("input_tokens", 0) or 0,
        output=u.get("output_tokens", 0) or 0,
        cache_write=u.get("cache_creation_input_tokens", 0) or 0,
        cache_read=u.get("cache_read_input_tokens", 0) or 0,
    )


def from_openai(u):
    """OpenAI usage (dict) to Usage. input_tokens includes cached tokens, so subtract them."""
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
    """Cost of usage in USD. discount is a multiplier, e.g. 0.5 for batch."""
    if model not in prices:
        raise KeyError(f"model not in price table: {model} (refusing to guess)")
    p = prices[model]
    total = (usage.input * p.input + usage.output * p.output
             + usage.cache_write * p.cache_write
             + usage.cache_read * p.cache_read) / 1_000_000
    return round(total * discount, 6)


def worst_case_usd(model, input_tokens, max_tokens, prices=PRICES):
    """Pre-call estimate: assume no input is cached and output runs all the way to max_tokens."""
    return cost_usd(model, Usage(input=input_tokens, output=max_tokens), prices)
