"""Cache hit rate, tool-result truncation, model cascade, currency conversion."""
from .pricing import Usage


def cache_hit_rate(usage):
    """Fraction of input read from cache (0 to 1)."""
    total_in = usage.input + usage.cache_write + usage.cache_read
    return usage.cache_read / total_in if total_in else 0.0


def truncate_tool_result(text, max_chars=4000, head=3000, tail=800):
    """When a tool result is too long, keep the head and tail and drop the middle."""
    if len(text) <= max_chars:
        return text
    omitted = len(text) - head - tail
    return f"{text[:head]}\n…({omitted} chars omitted; re-fetch with a range if needed)…\n{text[-tail:]}"


def cascade(prompt, call, models, accept):
    """Try models from cheapest up; return as soon as accept(text) is True.

    call(model, prompt) -> (text, Usage)
    Returns: (text, model used, total Usage, history of attempts)
    """
    total = Usage()
    tried = []
    text = None
    for model in models:
        text, usage = call(model, prompt)
        total = total + usage
        ok = accept(text)
        tried.append((model, ok))
        if ok:
            return text, model, total, tried
    return text, models[-1], total, tried


def usd_to_jpy(usd, rate):
    """Does not fetch exchange rates. Enter the rate actually used on your bill."""
    return round(usd * rate)
