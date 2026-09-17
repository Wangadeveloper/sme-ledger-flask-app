"""Validate and normalize transaction data extracted from SMS or provided by API."""

REQUIRED_FIELDS = [
    "reference",
    "amount",
    "type",
    "domain",
    "entity",
]

ALLOWED_TYPES = {"income", "expense", "transfer", "fuliza", "loan", "reversal", "withdrawal"}
ALLOWED_DOMAINS = {"mpesa", "banking", "pochi", "paybill", "till", "airtime", "other"}
ALLOWED_CATEGORIES = {"food", "utilities", "inventory", "salary", "transport", "sales", "transfers", "services", "loans", "other"}

def validate_transaction(data: dict) -> tuple[bool, list[str]]:
    """Validate transaction dictionary and return (is_valid, list_of_errors)."""
    errors = []

    if not isinstance(data, dict):
        return False, ["Invalid payload: must be a JSON object."]

    # Handle reference / transaction_id key variations
    ref = data.get("reference") or data.get("transaction_id")
    if not ref:
        errors.append("missing field: reference or transaction_id")

    amount = data.get("amount")
    if amount is None:
        errors.append("missing field: amount")
    else:
        try:
            amt_val = float(amount)
            if amt_val < 0:
                errors.append("invalid amount: must be non-negative")
        except (ValueError, TypeError):
            errors.append("invalid amount: must be numeric")

    t_type = (data.get("type") or "expense").lower()
    if t_type not in ALLOWED_TYPES:
        errors.append(f"invalid type: '{t_type}'. Must be one of {sorted(list(ALLOWED_TYPES))}")

    domain = (data.get("domain") or "mpesa").lower()
    if domain not in ALLOWED_DOMAINS:
        errors.append(f"invalid domain: '{domain}'. Must be one of {sorted(list(ALLOWED_DOMAINS))}")

    entity = data.get("entity")
    if not entity or not str(entity).strip():
        errors.append("missing field: entity")

    return len(errors) == 0, errors


def normalize_transaction(data: dict) -> dict:
    """Normalize fields in transaction data to standard values."""
    normalized = dict(data)

    # Reference code
    ref = normalized.get("reference") or normalized.get("transaction_id") or "TXN_UNKN"
    normalized["reference"] = str(ref).strip().upper()
    normalized["transaction_id"] = normalized["reference"]

    # Amount, Fee, Balance
    try:
        normalized["amount"] = abs(float(normalized.get("amount", 0.0)))
    except (ValueError, TypeError):
        normalized["amount"] = 0.0

    try:
        normalized["fee"] = abs(float(normalized.get("fee", 0.0)))
    except (ValueError, TypeError):
        normalized["fee"] = 0.0

    try:
        normalized["balance"] = abs(float(normalized.get("balance", 0.0)))
    except (ValueError, TypeError):
        normalized["balance"] = 0.0

    # Type & Domain
    normalized["type"] = str(normalized.get("type") or "expense").lower()
    if normalized["type"] not in ALLOWED_TYPES:
        normalized["type"] = "expense"

    normalized["domain"] = str(normalized.get("domain") or "mpesa").lower()
    if normalized["domain"] not in ALLOWED_DOMAINS:
        normalized["domain"] = "mpesa"

    # Category
    cat = str(normalized.get("category") or "other").lower()
    normalized["category"] = cat if cat in ALLOWED_CATEGORIES else "other"

    # Entity
    entity = str(normalized.get("entity") or "Unknown Merchant").strip().title()
    normalized["entity"] = entity

    # Status
    status = str(normalized.get("status") or "completed").lower()
    normalized["status"] = status if status in ["completed", "failed", "reversed", "pending"] else "completed"

    return normalized
