"""
Central configuration for the synthetic SaaS data generator.
Tweak volumes/dates here without touching generation logic.
"""

from datetime import date

# --- Random seed (reproducibility) ---
SEED = 42

# --- Simulation window ---
# 3 years of company history: gives real seasonality + growth-curve room
START_DATE = date(2022, 1, 1)
END_DATE = date(2024, 12, 31)

# --- Volumes ---
N_CUSTOMERS = 9000

# --- Plans (fixed dimension table) ---
# tier: lower number = cheaper/lower tier. Used to drive churn-by-tier logic.
PLANS = [
    {"plan_id": 1, "plan_name": "Free",            "tier": 0, "monthly_price": 0,    "billing_interval": "monthly"},
    {"plan_id": 2, "plan_name": "Starter",         "tier": 1, "monthly_price": 15,   "billing_interval": "monthly"},
    {"plan_id": 3, "plan_name": "Starter Annual",  "tier": 1, "monthly_price": 12,   "billing_interval": "annual"},
    {"plan_id": 4, "plan_name": "Pro",              "tier": 2, "monthly_price": 49,   "billing_interval": "monthly"},
    {"plan_id": 5, "plan_name": "Pro Annual",       "tier": 2, "monthly_price": 39,   "billing_interval": "annual"},
    {"plan_id": 6, "plan_name": "Business",         "tier": 3, "monthly_price": 149,  "billing_interval": "monthly"},
    {"plan_id": 7, "plan_name": "Business Annual",  "tier": 3, "monthly_price": 119,  "billing_interval": "annual"},
    {"plan_id": 8, "plan_name": "Enterprise",       "tier": 4, "monthly_price": 499,  "billing_interval": "monthly"},
]

# Base monthly churn probability by tier (0=Free churns fastest, 4=Enterprise churns slowest)
CHURN_PROB_BY_TIER = {
    0: 0.12,
    1: 0.06,
    2: 0.035,
    3: 0.02,
    4: 0.008,
}

# Probability an active customer upgrades / downgrades in a given month
UPGRADE_PROB_PER_MONTH = 0.03
DOWNGRADE_PROB_PER_MONTH = 0.015
REACTIVATION_PROB_PER_MONTH = 0.02  # for canceled customers

# --- Acquisition channels (with intentional nulls to simulate real-world gaps) ---
ACQUISITION_CHANNELS = ["organic", "paid_search", "referral", "social", "partner", None]
ACQUISITION_CHANNEL_WEIGHTS = [0.30, 0.25, 0.15, 0.15, 0.10, 0.05]

COUNTRIES = ["US", "GB", "CA", "AU", "DE", "FR", "IN", "BR", "NL", "SG"]
COUNTRY_WEIGHTS = [0.35, 0.12, 0.08, 0.06, 0.08, 0.06, 0.10, 0.06, 0.05, 0.04]

COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-1000", "1000+"]
COMPANY_SIZE_WEIGHTS = [0.40, 0.30, 0.15, 0.10, 0.05]

# --- Payment status distribution ---
PAYMENT_STATUS_WEIGHTS = {"succeeded": 0.92, "failed": 0.05, "refunded": 0.03}

# --- Messiness knobs (deliberate, to give the staging layer real work to do) ---
DUPLICATE_PAYMENT_RATE = 0.015       # simulate webhook double-fires
CURRENCY_CASING_NOISE_RATE = 0.05    # 'usd' vs 'USD'
ORPHANED_EVENT_RATE = 0.01           # event pointing at a subscription id that won't resolve cleanly
LATE_ARRIVING_EVENT_RATE = 0.03      # loaded_at noticeably after event_date
