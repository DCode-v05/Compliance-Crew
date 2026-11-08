"""Generate synthetic bank data for the Evidence Checker.

Produces two CSVs in ``data/synthetic_bank/``:
  - customers.csv (10,000 rows)
  - transactions.csv (50,000 rows)

Plants deliberate violations so the Evidence Checker has real failures to
find:
  - 50 high-risk customers with kyc_last_updated > 2 years ago
  - 30 medium-risk customers with kyc_last_updated > 8 years ago
  - 5 customers with kyc_last_updated missing entirely
  - 200 transactions above INR 10 lakh that are NOT flagged

Deterministic via a fixed random seed so the demo reproduces row IDs."""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path("data/synthetic_bank")
SEED = 42
TODAY = date(2026, 5, 23)

N_CUSTOMERS = 10_000
N_TRANSACTIONS = 50_000

N_HIGH_RISK_KYC_VIOLATIONS = 50
N_MEDIUM_RISK_KYC_VIOLATIONS = 30
N_MISSING_KYC = 5
N_UNFLAGGED_LARGE_TXNS = 200

INDIAN_FIRST_NAMES = [
    "Ramesh", "Priya", "Mohammed", "Anjali", "Suresh", "Lakshmi", "Vikram",
    "Pooja", "Arjun", "Sneha", "Rajesh", "Kavita", "Amit", "Deepa", "Sanjay",
    "Meera", "Vijay", "Anita", "Ravi", "Sunita", "Kiran", "Nisha", "Manoj",
    "Rekha", "Naveen", "Shanti", "Pradeep", "Geeta", "Ashok", "Saraswati",
]
INDIAN_LAST_NAMES = [
    "Kumar", "Sharma", "Singh", "Reddy", "Patel", "Iyer", "Khan", "Das",
    "Mishra", "Nair", "Gupta", "Joshi", "Pillai", "Naidu", "Verma", "Chowdhury",
    "Rao", "Sinha", "Menon", "Banerjee", "Ali", "Mehta", "Shah", "Yadav",
]
BRANCH_CODES = [
    "CBI-BLR-001", "CBI-BLR-002", "CBI-BLR-003", "CBI-CHN-001", "CBI-CHN-002",
    "CBI-DEL-001", "CBI-DEL-002", "CBI-MUM-001", "CBI-MUM-002", "CBI-KOL-001",
    "CBI-HYD-001", "CBI-PUN-001",
]
CHANNELS = ["branch", "online", "atm", "mobile"]


def _date_str(d: date | None) -> str:
    return d.isoformat() if d else ""


def _days_since(d: date | None) -> int:
    return (TODAY - d).days if d else -1


def generate_customers(rng: random.Random) -> pd.DataFrame:
    rows: list[dict] = []
    indices = list(range(N_CUSTOMERS))
    rng.shuffle(indices)
    violation_high = set(indices[:N_HIGH_RISK_KYC_VIOLATIONS])
    violation_medium = set(
        indices[N_HIGH_RISK_KYC_VIOLATIONS : N_HIGH_RISK_KYC_VIOLATIONS + N_MEDIUM_RISK_KYC_VIOLATIONS]
    )
    missing_kyc = set(
        indices[
            N_HIGH_RISK_KYC_VIOLATIONS
            + N_MEDIUM_RISK_KYC_VIOLATIONS : N_HIGH_RISK_KYC_VIOLATIONS
            + N_MEDIUM_RISK_KYC_VIOLATIONS
            + N_MISSING_KYC
        ]
    )

    for i in range(N_CUSTOMERS):
        customer_id = f"CUST-{i + 1:05d}"
        name = f"{rng.choice(INDIAN_FIRST_NAMES)} {rng.choice(INDIAN_LAST_NAMES)}"
        branch = rng.choice(BRANCH_CODES)

        account_open = TODAY - timedelta(days=rng.randint(30, 365 * 15))

        if i in violation_high:
            risk = "high"
        elif i in violation_medium:
            risk = "medium"
        elif i in missing_kyc:
            risk = rng.choice(["low", "medium", "high"])
        else:
            risk = rng.choices(["low", "medium", "high"], weights=[55, 35, 10])[0]

        if i in missing_kyc:
            kyc_last: date | None = None
        elif i in violation_high:
            kyc_last = TODAY - timedelta(days=rng.randint(731, 1500))
        elif i in violation_medium:
            kyc_last = TODAY - timedelta(days=rng.randint(2921, 3600))
        else:
            if risk == "high":
                kyc_last = TODAY - timedelta(days=rng.randint(30, 720))
            elif risk == "medium":
                kyc_last = TODAY - timedelta(days=rng.randint(30, 2900))
            else:
                kyc_last = TODAY - timedelta(days=rng.randint(30, 3600))
            if kyc_last < account_open:
                kyc_last = account_open + timedelta(days=rng.randint(0, 60))

        rows.append(
            {
                "customer_id": customer_id,
                "name": name,
                "risk_category": risk,
                "kyc_last_updated": _date_str(kyc_last),
                "days_since_last_kyc": _days_since(kyc_last),
                "account_open_date": _date_str(account_open),
                "branch_code": branch,
            }
        )

    return pd.DataFrame(rows)


def generate_transactions(rng: random.Random, customer_df: pd.DataFrame) -> pd.DataFrame:
    customer_ids = customer_df["customer_id"].tolist()
    rows: list[dict] = []

    indices = list(range(N_TRANSACTIONS))
    rng.shuffle(indices)
    unflagged_violations = set(indices[:N_UNFLAGGED_LARGE_TXNS])

    for i in range(N_TRANSACTIONS):
        txn_id = f"TXN-{i + 1:06d}"
        customer_id = rng.choice(customer_ids)
        txn_date = TODAY - timedelta(days=rng.randint(0, 365))
        channel = rng.choice(CHANNELS)

        if i in unflagged_violations:
            amount = float(rng.randint(1_000_001, 5_000_000))
            flagged = 0
        else:
            if rng.random() < 0.02:
                amount = float(rng.randint(1_000_001, 5_000_000))
                flagged = 1
            else:
                amount = round(rng.uniform(100, 200_000), 2)
                flagged = 0

        rows.append(
            {
                "transaction_id": txn_id,
                "customer_id": customer_id,
                "amount_inr": amount,
                "txn_date": _date_str(txn_date),
                "channel": channel,
                "flagged": flagged,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {N_CUSTOMERS} customers...")
    customers = generate_customers(rng)
    customers_path = OUTPUT_DIR / "customers.csv"
    customers.to_csv(customers_path, index=False)
    print(f"  wrote {customers_path}")

    print(f"Generating {N_TRANSACTIONS} transactions...")
    transactions = generate_transactions(rng, customers)
    transactions_path = OUTPUT_DIR / "transactions.csv"
    transactions.to_csv(transactions_path, index=False)
    print(f"  wrote {transactions_path}")

    high_risk_old_kyc = customers.query(
        "risk_category == 'high' and (days_since_last_kyc > 730 or days_since_last_kyc < 0)"
    )
    medium_risk_old_kyc = customers.query(
        "risk_category == 'medium' and days_since_last_kyc > 2920"
    )
    missing = customers.query("days_since_last_kyc < 0")
    unflagged_large = transactions.query("amount_inr > 1000000 and flagged == 0")

    print("\nPlanted violation summary (deterministic, seed=42):")
    print(f"  High-risk customers with KYC > 2y old (or missing): {len(high_risk_old_kyc)}")
    print(f"  Medium-risk customers with KYC > 8y old:            {len(medium_risk_old_kyc)}")
    print(f"  Customers with no KYC date:                         {len(missing)}")
    print(f"  Unflagged transactions > 10 lakh:                   {len(unflagged_large)}")


if __name__ == "__main__":
    main()
