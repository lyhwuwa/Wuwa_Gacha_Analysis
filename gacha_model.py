"""79-pull, 50/50 model from the supplied probability curve (no coral refunds)."""
from functools import lru_cache

import numpy as np

HARD_PITY = 79


def gold_probability(n):
    if not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError("抽数须为正整数")
    if n >= HARD_PITY:
        return 1.0
    if n <= 65:
        return 0.008
    if n <= 70:
        return 0.008 + 0.04 * (n - 65)
    if n <= 75:
        return 0.208 + 0.08 * (n - 70)
    return 0.608 + 0.10 * (n - 75)


PROBABILITIES = np.array([gold_probability(n) for n in range(1, 80)])
SURVIVAL = np.r_[1.0, np.cumprod(1 - PROBABILITIES)]
CDF = 1 - SURVIVAL[1:]
CDF[-1] = 1.0
MEAN_GOLD = float(SURVIVAL[:-1].sum())
MEAN_UP = 1.5 * MEAN_GOLD


def validate(pulls, pity=0):
    if not isinstance(pulls, (int, np.integer)) or not 0 <= pulls <= 100000:
        raise ValueError("总抽数须为0–100,000的整数")
    if not isinstance(pity, (int, np.integer)) or not 0 <= pity < HARD_PITY:
        raise ValueError("垫抽须为0–78的整数")


@lru_cache(maxsize=64)
def exact_expectations(pulls, pity=0, guaranteed=False):
    """Expected gold/UP counts at a fixed budget, including unfinished final pity."""
    validate(pulls, pity)
    small, big = np.zeros(HARD_PITY), np.zeros(HARD_PITY)
    (big if guaranteed else small)[pity] = 1.0
    gold = up = 0.0
    failure = 1 - PROBABILITIES
    for _ in range(pulls):
        small_hit = float(small @ PROBABILITIES)
        big_hit = float(big @ PROBABILITIES)
        up_hit = small_hit * 0.5 + big_hit
        gold += small_hit + big_hit
        up += up_hit
        small[1:] = small[:-1] * failure[:-1]
        big[1:] = big[:-1] * failure[:-1]
        small[0], big[0] = up_hit, small_hit * 0.5
    return {
        "gold": gold, "up": up, "mean_gold": MEAN_GOLD, "mean_up": MEAN_UP,
        "cost_up": pulls / up if up else None,
        "end_pity": float((small + big) @ np.arange(HARD_PITY)),
        "end_guarantee": float(big.sum()), "probability_mass": float((small + big).sum()),
    }


def sample_account(pulls, pity=0, guaranteed=False, seed=0):
    validate(pulls, pity)
    rng = np.random.default_rng(seed)
    draw = gold = up = last_up = 0
    events = []
    while draw < pulls:
        previous = 1 - SURVIVAL[pity]
        u = previous + SURVIVAL[pity] * rng.random()
        age = min(HARD_PITY, int(np.searchsorted(CDF, u, side="right")) + 1)
        gap = age - pity
        if draw + gap > pulls:
            pity += pulls - draw
            break
        draw += gap
        is_up = bool(guaranteed or rng.random() < 0.5)
        gold += 1
        up += int(is_up)
        events.append({"出金序号": gold, "本次第几抽": draw,
                       "结果": "大保底UP" if guaranteed else "UP" if is_up else "歪",
                       "出金间隔": age, "UP周期投入": draw - last_up if is_up else None})
        if is_up:
            last_up = draw
        guaranteed, pity = not is_up, 0
    return {"gold": gold, "up": up, "events": events, "end_pity": pity,
            "end_guarantee": guaranteed, "tail_after_up": pulls - last_up}


def simulate(pulls, trials=100000, pity=0, guaranteed=False, seed=20261022):
    """Vectorized inverse-CDF simulation; every trial starts independently."""
    validate(pulls, pity)
    if not isinstance(trials, (int, np.integer)) or not 1 <= trials <= 100000:
        raise ValueError("模拟账号数须为1–100,000的整数")
    if pulls * trials > 1_000_000_000:
        raise ValueError("模拟规模过大，请降低账号数或每账号抽数")
    if not isinstance(seed, (int, np.integer)) or not 0 <= seed <= 4294967295:
        raise ValueError("随机种子须为0–4,294,967,295的整数")
    rng = np.random.default_rng(seed)
    remaining = np.full(trials, pulls, dtype=np.int64)
    ages = np.full(trials, pity, dtype=np.int64)
    guarantees = np.full(trials, guaranteed, dtype=bool)
    gold, up = np.zeros(trials, dtype=np.int64), np.zeros(trials, dtype=np.int64)
    active = np.flatnonzero(remaining)
    while active.size:
        survival = SURVIVAL[ages[active]]
        values = 1 - survival + survival * rng.random(active.size)
        next_ages = np.minimum(HARD_PITY, np.searchsorted(CDF, values, side="right") + 1)
        gaps = next_ages - ages[active]
        hit = gaps <= remaining[active]
        done = active[~hit]
        ages[done] += remaining[done]
        remaining[done] = 0
        hit_ids = active[hit]
        if not hit_ids.size:
            break
        remaining[hit_ids] -= gaps[hit]
        ages[hit_ids] = 0
        is_up = guarantees[hit_ids] | (rng.random(hit_ids.size) < 0.5)
        gold[hit_ids] += 1
        up[hit_ids] += is_up
        guarantees[hit_ids] = ~is_up
        active = hit_ids[remaining[hit_ids] > 0]
    positive = up > 0
    return {
        "pulls": pulls, "trials": trials, "pity": pity, "guaranteed": bool(guaranteed), "seed": seed,
        "up_counts": up, "gold_counts": gold,
        "up_mean": float(up.mean()), "gold_mean": float(gold.mean()),
        "up_se": float(up.std() / np.sqrt(trials)), "gold_se": float(gold.std() / np.sqrt(trials)),
        "pooled_cost": float(pulls * trials / up.sum()) if up.sum() else None,
        "account_cost": float((pulls / up[positive]).mean()) if positive.any() else None,
        "positive_accounts": int(positive.sum()),
        "sample": sample_account(pulls, pity, guaranteed, seed ^ 0x9E3779B9),
    }


def percentile_interval(counts, actual):
    """Discrete mid-rank must not be mistaken for a precise individual rank."""
    counts = np.asarray(counts)
    return float((counts < actual).mean()), float((counts <= actual).mean())
