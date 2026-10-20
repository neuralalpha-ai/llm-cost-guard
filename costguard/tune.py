"""キャッシュ率・ツール結果の切り詰め・モデルのカスケード・円換算。"""
from .pricing import Usage


def cache_hit_rate(usage):
    """入力のうちキャッシュから読めた割合（0〜1）。"""
    total_in = usage.input + usage.cache_write + usage.cache_read
    return usage.cache_read / total_in if total_in else 0.0


def truncate_tool_result(text, max_chars=4000, head=3000, tail=800):
    """ツールの結果が長すぎるとき、先頭と末尾を残して中を省く。"""
    if len(text) <= max_chars:
        return text
    omitted = len(text) - head - tail
    return f"{text[:head]}\n…（{omitted}文字省略。必要なら範囲を指定して再取得）…\n{text[-tail:]}"


def cascade(prompt, call, models, accept):
    """安いモデルから順に試し、accept(text) が True の時点で返す。

    call(model, prompt) -> (text, Usage)
    戻り値: (text, 使ったモデル, 合計Usage, 試した履歴)
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
    """為替は自動取得しない。請求に使われるレートを自分で入れる。"""
    return round(usd * rate)
