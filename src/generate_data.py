"""Generate synthetic e-commerce data for the A/B-testing and attribution case study.

Outputs (data/raw/):
    experiment_users.csv   one row per user in a 14-day checkout-redesign A/B test
    journeys.csv           one row per marketing journey (converted flag, revenue)
    touchpoints.csv        one row per marketing touch, ordered within journey
    channel_spend.csv      quarterly spend by channel

Both datasets are simulated from known processes (documented below) so the
analysis can be checked against ground truth. Deterministic (seed=42).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42

# =============================================================================
# 1. A/B test: one-page checkout redesign
# =============================================================================
N_USERS = 124_000
DEVICES = ["mobile", "desktop", "tablet"]
DEVICE_P = [0.60, 0.35, 0.05]
BASE_CONV = {"desktop": 0.050, "mobile": 0.034, "tablet": 0.042}       # control, new visitors
RETURNING_MULT = 1.8
TRUE_REL_LIFT = {"mobile": 0.14, "desktop": 0.03, "tablet": 0.05}      # treatment effect on conversion
TRUE_AOV_LIFT = 0.015
EXPERIMENT_START = pd.Timestamp("2026-03-02")
EXPERIMENT_DAYS = 14

# =============================================================================
# 2. Attribution: Markov-chain customer journeys (the "true" process)
# =============================================================================
CHANNELS = ["paid_search", "paid_social", "email", "organic_search", "display", "affiliate", "direct"]
START_P = {"display": .20, "paid_social": .20, "organic_search": .22, "paid_search": .15,
           "affiliate": .08, "email": .05, "direct": .10}
P_CONVERT = {"display": .003, "paid_social": .008, "affiliate": .012, "organic_search": .018,
             "paid_search": .025, "email": .040, "direct": .045}
P_EXIT = {"display": .45, "paid_social": .40, "affiliate": .35, "organic_search": .30,
          "paid_search": .30, "email": .25, "direct": .22}
NEXT_W = {   # relative weights of the next channel, scaled to the remaining probability mass
    "display":        {"paid_search": .20, "paid_social": .10, "email": .10, "organic_search": .25, "affiliate": .05, "direct": .15, "display": .15},
    "paid_social":    {"paid_search": .20, "email": .15, "organic_search": .20, "direct": .15, "display": .10, "affiliate": .05, "paid_social": .15},
    "paid_search":    {"email": .20, "direct": .25, "organic_search": .15, "paid_social": .05, "affiliate": .10, "display": .05, "paid_search": .20},
    "organic_search": {"email": .20, "direct": .25, "paid_search": .15, "paid_social": .05, "display": .05, "affiliate": .10, "organic_search": .20},
    "email":          {"direct": .30, "paid_search": .15, "organic_search": .20, "email": .15, "paid_social": .05, "display": .05, "affiliate": .10},
    "affiliate":      {"paid_search": .20, "email": .15, "direct": .25, "organic_search": .15, "affiliate": .15, "display": .05, "paid_social": .05},
    "direct":         {"email": .25, "paid_search": .15, "organic_search": .15, "direct": .30, "display": .03, "paid_social": .05, "affiliate": .07},
}
N_JOURNEYS = 100_000
MAX_TOUCHES = 10
# Illustrative quarterly spend (an assumption, not derived from the journeys); direct has no media cost.
SPEND = {"paid_search": 32_000, "paid_social": 30_000, "display": 22_000, "email": 8_000,
         "affiliate": 12_000, "organic_search": 25_000, "direct": 0}


def true_transition_matrix() -> pd.DataFrame:
    """Row-stochastic matrix over [START, channels..., CONVERSION, NULL] used to generate journeys."""
    states = ["START"] + CHANNELS + ["CONVERSION", "NULL"]
    T = pd.DataFrame(0.0, index=states, columns=states)
    for c, p in START_P.items():
        T.loc["START", c] = p
    for s in CHANNELS:
        rest = 1 - P_CONVERT[s] - P_EXIT[s]
        w = pd.Series(NEXT_W[s]); w = w / w.sum() * rest
        for c, v in w.items():
            T.loc[s, c] = v
        T.loc[s, "CONVERSION"] = P_CONVERT[s]
        T.loc[s, "NULL"] = P_EXIT[s]
    T.loc["CONVERSION", "CONVERSION"] = 1.0
    T.loc["NULL", "NULL"] = 1.0
    return T


def generate_experiment(rng: np.random.Generator) -> pd.DataFrame:
    n = N_USERS
    variant = rng.choice(["control", "treatment"], size=n)       # true 50/50 randomisation
    day = rng.integers(0, EXPERIMENT_DAYS, size=n)
    device = rng.choice(DEVICES, size=n, p=DEVICE_P)
    returning = rng.random(n) < 0.35
    value = rng.lognormal(0, 0.6, size=n)                        # latent customer value / propensity

    pre_spend = np.where(rng.random(n) < (0.25 + 0.5 * returning), rng.lognormal(np.log(35), 0.5, n) * value ** 1.2, 0.0)

    base = np.array([BASE_CONV[d] for d in device]) * np.where(returning, RETURNING_MULT, 1.0)
    prop = value ** 1.2 / np.mean(value ** 1.2)
    lift = np.array([TRUE_REL_LIFT[d] for d in device])
    p = base * prop * np.where(variant == "treatment", 1 + lift, 1.0)
    converted = rng.random(n) < np.clip(p, 0, 0.9)

    aov = rng.lognormal(np.log(55), 0.45, n) * value ** 0.8
    aov = aov * np.where(variant == "treatment", 1 + TRUE_AOV_LIFT, 1.0)
    order_value = np.where(converted, aov, 0.0).round(2)

    refunded = converted & (rng.random(n) < np.where(variant == "treatment", 0.062, 0.060))

    df = pd.DataFrame({
        "user_id": [f"U{i:06d}" for i in range(1, n + 1)],
        "variant": variant,
        "assigned_date": (EXPERIMENT_START + pd.to_timedelta(day, unit="D")).date,
        "device": device,
        "is_returning": returning.astype(int),
        "pre_period_spend": pre_spend.round(2),
        "converted": converted.astype(int),
        "order_value": order_value,
        "refunded": refunded.astype(int),
    })
    return df.sort_values(["assigned_date", "user_id"]).reset_index(drop=True)


def generate_journeys(rng: np.random.Generator):
    T = true_transition_matrix()
    nxt = {s: (list(T.columns), T.loc[s].values) for s in CHANNELS}
    start_states, start_p = CHANNELS, np.array([START_P[c] for c in CHANNELS])
    t0 = pd.Timestamp("2026-01-01")
    journeys, touches = [], []
    for j in range(1, N_JOURNEYS + 1):
        jid = f"J{j:06d}"
        start = t0 + pd.Timedelta(hours=float(rng.uniform(0, 24 * 89)))
        state = rng.choice(start_states, p=start_p)
        ts, order, converted = start, 0, 0
        while True:
            order += 1
            touches.append((jid, order, state, ts))
            cols, probs = nxt[state]
            nxt_state = rng.choice(cols, p=probs)
            if nxt_state == "CONVERSION":
                converted = 1
                break
            if nxt_state == "NULL" or order >= MAX_TOUCHES:
                break
            state = nxt_state
            ts = ts + pd.Timedelta(hours=float(rng.exponential(36)) + 0.5)
        conv_ts = ts + pd.Timedelta(minutes=float(rng.uniform(1, 90))) if converted else pd.NaT
        revenue = round(float(rng.lognormal(np.log(70), 0.5)), 2) if converted else 0.0
        journeys.append((jid, f"U{200000 + j}", converted, conv_ts, revenue))
    jdf = pd.DataFrame(journeys, columns=["journey_id", "user_id", "converted", "conversion_ts", "revenue"])
    tdf = pd.DataFrame(touches, columns=["journey_id", "touch_order", "channel", "touch_ts"])
    sdf = pd.DataFrame({"channel": list(SPEND), "spend": list(SPEND.values())})
    return jdf, tdf, sdf


def generate(out_dir: Path) -> None:
    rng = np.random.default_rng(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)
    exp = generate_experiment(rng)
    jdf, tdf, sdf = generate_journeys(rng)
    exp.to_csv(out_dir / "experiment_users.csv", index=False)
    jdf.to_csv(out_dir / "journeys.csv", index=False)
    tdf.to_csv(out_dir / "touchpoints.csv", index=False)
    sdf.to_csv(out_dir / "channel_spend.csv", index=False)
    print(f"experiment users={len(exp):,}  journeys={len(jdf):,} (converted {jdf.converted.mean():.1%})  touches={len(tdf):,}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data" / "raw"))
    generate(Path(ap.parse_args().out))
