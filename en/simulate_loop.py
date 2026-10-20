"""Calculate how an agent loop's input tokens grow, without calling the API.

Every turn resends "the whole conversation so far," so input grows each turn and the total grows with the square of the number of turns.
"""
from costguard import Usage, cost_usd

MODEL = "claude-sonnet-5-5"
SYSTEM = 6_000        # system prompt + tool definitions
PER_TURN = 1_500      # conversation added per turn (tool results + model messages)
OUT = 400             # output per turn


def run(turns, cached):
    total = Usage()
    for i in range(turns):
        history = SYSTEM + PER_TURN * i
        if cached and i > 0:
            # everything up to the previous turn is a cache read; only the new part is written
            u = Usage(input=0, output=OUT, cache_write=PER_TURN, cache_read=history - PER_TURN)
        elif cached:
            u = Usage(input=0, output=OUT, cache_write=history)
        else:
            u = Usage(input=history, output=OUT)
        total = total + u
    return total, cost_usd(MODEL, total)


if __name__ == "__main__":
    print(f"{'turns':>5}  {'input total (tok)':>17}  {'cost (no cache)':>15}  {'cost (cache)':>12}")
    for n in (5, 10, 20, 40, 80):
        u0, c0 = run(n, False)
        u1, c1 = run(n, True)
        print(f"{n:>5}  {u0.input:>17,}  {'$'+format(c0, '.3f'):>15}  {'$'+format(c1, '.3f'):>12}")
