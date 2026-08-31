"""
Synthetic SaaS data generator.

Produces 5 raw CSVs that mimic a messy real-world source-system export:
    customers.csv
    plans.csv
    subscriptions.csv
    subscription_events.csv
    payments.csv

Design goals (see README for full rationale):
  - Growth curve + seasonality in signups, not uniform random noise
  - Churn probability varies by plan tier (free churns fastest)
  - Subscriptions change over time (upgrades/downgrades/cancel/reactivate),
    forcing real state-tracking logic downstream in dbt
  - Deliberate mess in the raw layer: nulls, duplicate payment rows,
    inconsistent currency casing, orphaned events, late-arriving events
"""

import random
import uuid
from datetime import date, timedelta
from calendar import monthrange

import numpy as np
import pandas as pd
from faker import Faker

import config as cfg

random.seed(cfg.SEED)
np.random.seed(cfg.SEED)
fake = Faker()
Faker.seed(cfg.SEED)

OUT_DIR = "../raw_data"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def month_range(start: date, end: date):
    """List of first-of-month dates from start's month to end's month, inclusive."""
    months = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        months.append(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return months


def seasonal_multiplier(month: int) -> float:
    """Rough SaaS seasonality: Jan/Sep hiring pushes, Dec holiday dip."""
    factors = {1: 1.25, 2: 1.05, 3: 1.05, 4: 1.0, 5: 1.0, 6: 0.95,
               7: 0.85, 8: 0.9, 9: 1.2, 10: 1.1, 11: 1.0, 12: 0.6}
    return factors[month]


def build_signup_month_weights():
    """Growth-curve (roughly logistic ramp) x seasonality, per calendar month."""
    months = month_range(cfg.START_DATE, cfg.END_DATE)
    n = len(months)
    # logistic ramp from ~0.2x to ~1.8x of baseline across the window
    ramp = 0.2 + 1.6 / (1 + np.exp(-1 * (np.linspace(-6, 6, n))))
    weights = []
    for m, r in zip(months, ramp):
        weights.append(r * seasonal_multiplier(m.month))
    weights = np.array(weights)
    return months, weights / weights.sum()


def random_day_in_month(month_start: date) -> date:
    days_in_month = monthrange(month_start.year, month_start.month)[1]
    return month_start + timedelta(days=random.randint(0, days_in_month - 1))


def add_months(d: date, n: int) -> date:
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


# ----------------------------------------------------------------------
# 1. Plans (static dimension)
# ----------------------------------------------------------------------

def generate_plans() -> pd.DataFrame:
    return pd.DataFrame(cfg.PLANS)


PLANS_DF = generate_plans()
PLANS_BY_ID = {p["plan_id"]: p for p in cfg.PLANS}
# tier -> list of plan_ids available at that tier (monthly + annual variants)
PLAN_IDS_BY_TIER = {}
for p in cfg.PLANS:
    PLAN_IDS_BY_TIER.setdefault(p["tier"], []).append(p["plan_id"])

TIERS_SORTED = sorted(PLAN_IDS_BY_TIER.keys())


def pick_plan_for_tier(tier: int) -> int:
    """Pick a monthly/annual variant for a given tier (~70/30 monthly/annual)."""
    candidates = PLAN_IDS_BY_TIER[tier]
    if len(candidates) == 1:
        return candidates[0]
    monthly = [pid for pid in candidates if PLANS_BY_ID[pid]["billing_interval"] == "monthly"]
    annual = [pid for pid in candidates if PLANS_BY_ID[pid]["billing_interval"] == "annual"]
    return random.choice(monthly) if random.random() < 0.7 else random.choice(annual)


# ----------------------------------------------------------------------
# 2. Customers
# ----------------------------------------------------------------------

def generate_customers(n: int) -> pd.DataFrame:
    months, weights = build_signup_month_weights()
    rows = []
    for i in range(1, n + 1):
        signup_month = np.random.choice(months, p=weights)
        signup_date = random_day_in_month(signup_month)
        # slight null-injection on acquisition_channel handled by weighted None option
        channel = weighted_choice(cfg.ACQUISITION_CHANNELS, cfg.ACQUISITION_CHANNEL_WEIGHTS)
        rows.append({
            "customer_id": i,
            "signup_date": signup_date.isoformat(),
            "acquisition_channel": channel,
            "country": weighted_choice(cfg.COUNTRIES, cfg.COUNTRY_WEIGHTS),
            "company_size": weighted_choice(cfg.COMPANY_SIZES, cfg.COMPANY_SIZE_WEIGHTS),
            "email": fake.company_email(),
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 3. Subscriptions + subscription_events (state machine per customer)
# ----------------------------------------------------------------------

def initial_tier() -> int:
    return weighted_choice(TIERS_SORTED, [0.40, 0.32, 0.16, 0.09, 0.03])


def simulate_customer_lifecycle(customer_id: int, signup_date: date,
                                 sub_id_counter, event_id_counter):
    """Returns (subscription_rows, event_rows) for one customer."""
    sub_rows = []
    event_rows = []

    tier = initial_tier()
    plan_id = pick_plan_for_tier(tier)
    sub_id = next(sub_id_counter)
    period_start = signup_date
    status = "active"

    sub_rows.append({
        "subscription_id": sub_id, "customer_id": customer_id, "plan_id": plan_id,
        "start_date": period_start.isoformat(), "end_date": None, "status": "active",
    })
    event_rows.append({
        "event_id": next(event_id_counter), "subscription_id": sub_id,
        "event_type": "created", "event_date": period_start.isoformat(),
        "previous_plan_id": None, "new_plan_id": plan_id,
    })

    cursor = add_months(period_start, 1)
    canceled = False

    while cursor <= cfg.END_DATE:
        if status == "active":
            churn_p = cfg.CHURN_PROB_BY_TIER[tier]
            roll = random.random()
            if roll < churn_p:
                # churn this subscription record
                sub_rows[-1]["end_date"] = cursor.isoformat()
                sub_rows[-1]["status"] = "canceled"
                event_rows.append({
                    "event_id": next(event_id_counter), "subscription_id": sub_id,
                    "event_type": "canceled", "event_date": cursor.isoformat(),
                    "previous_plan_id": plan_id, "new_plan_id": None,
                })
                status = "canceled"
                canceled = True
            else:
                roll2 = random.random()
                new_tier = None
                if roll2 < cfg.UPGRADE_PROB_PER_MONTH and tier < max(TIERS_SORTED):
                    new_tier = tier + 1
                    change_type = "upgraded"
                elif roll2 < cfg.UPGRADE_PROB_PER_MONTH + cfg.DOWNGRADE_PROB_PER_MONTH and tier > min(TIERS_SORTED):
                    new_tier = tier - 1
                    change_type = "downgraded"

                if new_tier is not None:
                    new_plan_id = pick_plan_for_tier(new_tier)
                    # close current record
                    sub_rows[-1]["end_date"] = cursor.isoformat()
                    sub_rows[-1]["status"] = "superseded"
                    # open new record
                    sub_id = next(sub_id_counter)
                    sub_rows.append({
                        "subscription_id": sub_id, "customer_id": customer_id, "plan_id": new_plan_id,
                        "start_date": cursor.isoformat(), "end_date": None, "status": "active",
                    })
                    event_rows.append({
                        "event_id": next(event_id_counter), "subscription_id": sub_id,
                        "event_type": change_type, "event_date": cursor.isoformat(),
                        "previous_plan_id": plan_id, "new_plan_id": new_plan_id,
                    })
                    tier = new_tier
                    plan_id = new_plan_id

        elif status == "canceled":
            if random.random() < cfg.REACTIVATION_PROB_PER_MONTH:
                tier = initial_tier()
                plan_id = pick_plan_for_tier(tier)
                sub_id = next(sub_id_counter)
                sub_rows.append({
                    "subscription_id": sub_id, "customer_id": customer_id, "plan_id": plan_id,
                    "start_date": cursor.isoformat(), "end_date": None, "status": "active",
                })
                event_rows.append({
                    "event_id": next(event_id_counter), "subscription_id": sub_id,
                    "event_type": "reactivated", "event_date": cursor.isoformat(),
                    "previous_plan_id": None, "new_plan_id": plan_id,
                })
                status = "active"

        cursor = add_months(cursor, 1)

    return sub_rows, event_rows


def id_counter(start=1):
    n = start
    while True:
        yield n
        n += 1


def generate_subscriptions_and_events(customers_df: pd.DataFrame):
    sub_id_counter = id_counter(1)
    event_id_counter = id_counter(1)
    all_subs, all_events = [], []

    for _, row in customers_df.iterrows():
        signup_date = date.fromisoformat(row["signup_date"])
        subs, events = simulate_customer_lifecycle(
            row["customer_id"], signup_date, sub_id_counter, event_id_counter
        )
        all_subs.extend(subs)
        all_events.extend(events)

    subs_df = pd.DataFrame(all_subs)
    events_df = pd.DataFrame(all_events)

    # --- inject messiness: late-arriving events (loaded_at after event_date) ---
    def make_loaded_at(event_date_str):
        d = date.fromisoformat(event_date_str)
        if random.random() < cfg.LATE_ARRIVING_EVENT_RATE:
            d = d + timedelta(days=random.randint(2, 10))
        return d.isoformat()

    events_df["loaded_at"] = events_df["event_date"].apply(make_loaded_at)

    # keep plan id columns as clean nullable ints, not floats, despite NaNs
    events_df["previous_plan_id"] = events_df["previous_plan_id"].astype("Int64")
    events_df["new_plan_id"] = events_df["new_plan_id"].astype("Int64")

    # --- inject messiness: a handful of orphaned events (bad subscription_id) ---
    n_orphans = int(len(events_df) * cfg.ORPHANED_EVENT_RATE)
    orphan_idx = np.random.choice(events_df.index, size=n_orphans, replace=False)
    max_sub_id = subs_df["subscription_id"].max()
    events_df.loc[orphan_idx, "subscription_id"] = events_df.loc[orphan_idx, "subscription_id"].apply(
        lambda _: max_sub_id + random.randint(1000, 9999)
    )

    return subs_df, events_df


# ----------------------------------------------------------------------
# 4. Payments
# ----------------------------------------------------------------------

def generate_payments(subs_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pay_id = id_counter(1)

    for _, sub in subs_df.iterrows():
        plan = PLANS_BY_ID[sub["plan_id"]]
        price = plan["monthly_price"]
        if price == 0:
            continue  # free tier, no payments

        start = date.fromisoformat(sub["start_date"])
        end = date.fromisoformat(sub["end_date"]) if pd.notna(sub["end_date"]) else cfg.END_DATE
        step_months = 1 if plan["billing_interval"] == "monthly" else 12
        amount = price if plan["billing_interval"] == "monthly" else price * 12

        cursor = start
        while cursor <= end:
            status = weighted_choice(
                list(cfg.PAYMENT_STATUS_WEIGHTS.keys()),
                list(cfg.PAYMENT_STATUS_WEIGHTS.values()),
            )
            currency = "USD"
            if random.random() < cfg.CURRENCY_CASING_NOISE_RATE:
                currency = "usd"

            rows.append({
                "payment_id": next(pay_id),
                "subscription_id": sub["subscription_id"],
                "amount": amount,
                "currency": currency,
                "status": status,
                "payment_date": cursor.isoformat(),
            })
            cursor = add_months(cursor, step_months)

    payments_df = pd.DataFrame(rows)

    # --- inject messiness: duplicate rows (simulates webhook double-fires) ---
    n_dupes = int(len(payments_df) * cfg.DUPLICATE_PAYMENT_RATE)
    dupe_rows = payments_df.sample(n=n_dupes, random_state=cfg.SEED).copy()
    payments_df = pd.concat([payments_df, dupe_rows], ignore_index=True)
    payments_df = payments_df.sample(frac=1, random_state=cfg.SEED).reset_index(drop=True)

    return payments_df


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    import os
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Generating customers...")
    customers_df = generate_customers(cfg.N_CUSTOMERS)

    print("Generating plans...")
    plans_df = PLANS_DF

    print("Generating subscriptions + subscription_events (this is the slow step)...")
    subs_df, events_df = generate_subscriptions_and_events(customers_df)

    print("Generating payments...")
    payments_df = generate_payments(subs_df)

    customers_df.to_csv(f"{OUT_DIR}/customers.csv", index=False)
    plans_df.to_csv(f"{OUT_DIR}/plans.csv", index=False)
    subs_df.to_csv(f"{OUT_DIR}/subscriptions.csv", index=False)
    events_df.to_csv(f"{OUT_DIR}/subscription_events.csv", index=False)
    payments_df.to_csv(f"{OUT_DIR}/payments.csv", index=False)

    print("\nDone. Row counts:")
    print(f"  customers.csv:            {len(customers_df):,}")
    print(f"  plans.csv:                {len(plans_df):,}")
    print(f"  subscriptions.csv:        {len(subs_df):,}")
    print(f"  subscription_events.csv:  {len(events_df):,}")
    print(f"  payments.csv:             {len(payments_df):,}")


if __name__ == "__main__":
    main()
