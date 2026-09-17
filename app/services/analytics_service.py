"""Deterministic financial calculations using Pandas.

Adheres to the SME-Ledger architecture: language parsing handles SMS,
while deterministic Pandas handles exact financial arithmetic.
"""

import pandas as pd
from typing import List, Dict, Any

def build_financial_profile(transactions: List[Any]) -> Dict[str, Any]:
    """Compute comprehensive SME financial profile using Pandas."""
    if not transactions:
        return {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "net_cash_flow": 0.0,
            "current_balance": 0.0,
            "transaction_count": 0,
            "surplus_rate": 0.0,
            "expense_rate": 0.0,
            "income_to_expense_ratio": 0.0,
            "average_income": 0.0,
            "average_expense": 0.0,
            "top_spending_categories": {},
            "top_spending_entities": {},
            "top_income_sources": {},
            "domain_breakdown": {},
            "daily_trends": [],
            "financial_health_signals": {
                "health_rating": "No Data",
                "fuliza_debt_alert": False,
                "cash_flow_status": "Neutral",
            }
        }

    # Convert SQLAlchemy model objects or dicts into plain dictionaries
    raw_list = []
    for item in transactions:
        if hasattr(item, "to_dict"):
            raw_list.append(item.to_dict())
        elif isinstance(item, dict):
            raw_list.append(item)

    df = pd.DataFrame(raw_list)

    # Normalize type column name
    if "type" not in df.columns and "transaction_type" in df.columns:
        df["type"] = df["transaction_type"]
    elif "transaction_type" not in df.columns and "type" in df.columns:
        df["transaction_type"] = df["type"]

    # Ensure required columns exist
    for col in ["amount", "fee", "balance", "type", "domain", "category", "entity", "date"]:
        if col not in df.columns:
            df[col] = 0.0 if col in ["amount", "fee", "balance"] else "unknown"

    # Fill NA values
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["fee"] = pd.to_numeric(df["fee"], errors="coerce").fillna(0.0)
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce").fillna(0.0)
    df["type"] = df["type"].astype(str).str.lower()

    # Filter income vs expenses
    income_df = df[df["type"] == "income"]
    expense_df = df[df["type"].isin(["expense", "fuliza", "withdrawal", "transfer"])]

    total_income = float(income_df["amount"].sum())
    total_expenses = float(expense_df["amount"].sum())
    net_cash_flow = total_income - total_expenses

    # Current balance: get latest balance from ledger if available
    current_balance = 0.0
    if "balance" in df.columns and len(df[df["balance"] > 0]) > 0:
        current_balance = float(df[df["balance"] > 0].iloc[-1]["balance"])
    else:
        current_balance = max(0.0, net_cash_flow)

    # Ratios
    surplus_rate = 0.0
    expense_rate = 0.0
    if total_income > 0:
        surplus_rate = (net_cash_flow / total_income) * 100.0
        expense_rate = (total_expenses / total_income) * 100.0

    inc_exp_ratio = (total_income / total_expenses) if total_expenses > 0 else (total_income if total_income > 0 else 1.0)

    avg_income = float(income_df["amount"].mean()) if len(income_df) > 0 else 0.0
    avg_expense = float(expense_df["amount"].mean()) if len(expense_df) > 0 else 0.0

    # Top spending categories
    top_categories = {}
    if len(expense_df) > 0:
        cat_grp = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_categories = {str(k): float(v) for k, v in cat_grp.items()}

    # Top spending entities / merchants
    top_entities = {}
    if len(expense_df) > 0:
        ent_grp = expense_df.groupby("entity")["amount"].sum().sort_values(ascending=False)
        top_entities = {str(k): float(v) for k, v in ent_grp.head(5).items()}

    # Top income sources
    top_income = {}
    if len(income_df) > 0:
        inc_grp = income_df.groupby("entity")["amount"].sum().sort_values(ascending=False)
        top_income = {str(k): float(v) for k, v in inc_grp.head(5).items()}

    # Domain breakdown
    domain_counts = {}
    if "domain" in df.columns:
        dom_grp = df.groupby("domain")["amount"].agg(["count", "sum"])
        for dom, row in dom_grp.iterrows():
            domain_counts[str(dom)] = {
                "count": int(row["count"]),
                "total_amount": float(row["sum"])
            }

    # Time series daily trends
    daily_trends = []
    if "date" in df.columns:
        # Format date string
        df["clean_date"] = df["date"].astype(str).str.slice(0, 10)
        dates = sorted(df["clean_date"].unique())
        for d in dates:
            day_inc = float(df[(df["clean_date"] == d) & (df["type"] == "income")]["amount"].sum())
            day_exp = float(df[(df["clean_date"] == d) & (df["type"].isin(["expense", "fuliza", "withdrawal", "transfer"]))]["amount"].sum())
            daily_trends.append({
                "date": d,
                "income": day_inc,
                "expense": day_exp
            })

    # Financial Health Signals
    fuliza_alert = bool((df["type"] == "fuliza").any() or (df["domain"] == "fuliza").any())
    health_rating = "Healthy"
    if net_cash_flow < 0:
        health_rating = "Critical Deficit"
    elif surplus_rate < 10:
        health_rating = "Tight Margin"
    elif surplus_rate >= 25:
        health_rating = "Strong Surplus"

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "current_balance": round(current_balance, 2),
        "transaction_count": len(df),
        "surplus_rate": round(surplus_rate, 1),
        "expense_rate": round(expense_rate, 1),
        "income_to_expense_ratio": round(inc_exp_ratio, 2),
        "average_income": round(avg_income, 2),
        "average_expense": round(avg_expense, 2),
        "top_spending_categories": top_categories,
        "top_spending_entities": top_entities,
        "top_income_sources": top_income,
        "domain_breakdown": domain_counts,
        "daily_trends": daily_trends,
        "financial_health_signals": {
            "health_rating": health_rating,
            "fuliza_debt_alert": fuliza_alert,
            "cash_flow_status": "Positive" if net_cash_flow >= 0 else "Negative",
        }
    }
