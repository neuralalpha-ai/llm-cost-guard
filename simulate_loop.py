"""APIを呼ばずに、エージェントループの入力トークンがどう増えるかを計算する。

毎ターン「それまでの会話全部」を送り直すので、入力は周回ごとに増え、合計は周回数の2乗で増える。
"""
from costguard import Usage, cost_usd

MODEL = "claude-sonnet-5-5"
SYSTEM = 6_000        # システムプロンプト＋ツール定義
PER_TURN = 1_500      # 1周で増える会話（ツール結果＋モデルの発言）
OUT = 400             # 1周の出力


def run(turns, cached):
    total = Usage()
    for i in range(turns):
        history = SYSTEM + PER_TURN * i
        if cached and i > 0:
            # 前の周までの部分はキャッシュ読み取り、新しい分だけ書き込み
            u = Usage(input=0, output=OUT, cache_write=PER_TURN, cache_read=history - PER_TURN)
        elif cached:
            u = Usage(input=0, output=OUT, cache_write=history)
        else:
            u = Usage(input=history, output=OUT)
        total = total + u
    return total, cost_usd(MODEL, total)


if __name__ == "__main__":
    print(f"{'周回':>4} {'入力合計(tok)':>14} {'費用(キャッシュなし)':>18} {'費用(キャッシュあり)':>18}")
    for n in (5, 10, 20, 40, 80):
        u0, c0 = run(n, False)
        u1, c1 = run(n, True)
        print(f"{n:>4} {u0.input:>14,} {'$'+format(c0, '.3f'):>18} {'$'+format(c1, '.3f'):>18}")
