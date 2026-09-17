import io
import csv
from datetime import datetime
from flask import Blueprint, jsonify, request, Response
from app.models import db
from app.models.transaction import Transaction
from app.services.model_service import ModelService
from app.services.validation_service import validate_transaction, normalize_transaction
from app.services.analytics_service import build_financial_profile

api_bp = Blueprint("api", __name__)
model_service = ModelService()

@api_bp.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "sme-ledger",
        "mode": "on-device-4gb-optimized",
        "engine": model_service.engine
    })

@api_bp.post("/extract")
def extract_transaction():
    """Extract structured transaction details from raw SMS text."""
    data = request.get_json(silent=True) or {}
    sms_text = data.get("sms", "").strip()
    sms_list = data.get("sms_list", [])
    auto_save = data.get("auto_save", False)

    if not sms_text and not sms_list:
        return jsonify({"error": "sms or sms_list is required"}), 400

    results = []
    messages = sms_list if sms_list else [sms_text]

    for sms in messages:
        if not sms.strip():
            continue

        raw_extracted = model_service.extract_transaction(sms)
        is_valid, errors = validate_transaction(raw_extracted)
        normalized = normalize_transaction(raw_extracted)

        saved = False
        txn_id = None

        if auto_save and is_valid:
            existing = Transaction.query.filter_by(reference=normalized["reference"]).first()
            if not existing:
                txn = Transaction(
                    reference=normalized["reference"],
                    raw_sms=sms,
                    domain=normalized["domain"],
                    transaction_type=normalized["type"],
                    entity=normalized["entity"],
                    amount=normalized["amount"],
                    fee=normalized["fee"],
                    balance=normalized["balance"],
                    category=normalized["category"],
                    status=normalized["status"],
                    date=normalized["date"],
                    time=normalized["time"]
                )
                db.session.add(txn)
                db.session.commit()
                saved = True
                txn_id = txn.id

        results.append({
            "sms": sms,
            "extracted": normalized,
            "is_valid": is_valid,
            "validation_errors": errors,
            "saved": saved,
            "transaction_id": txn_id
        })

    if len(results) == 1:
        return jsonify(results[0])

    return jsonify({"count": len(results), "items": results})

@api_bp.get("/transactions")
def list_transactions():
    """List transactions with optional filtering and pagination."""
    domain = request.args.get("domain")
    category = request.args.get("category")
    t_type = request.args.get("type")
    search = request.args.get("q")

    query = Transaction.query

    if domain:
        query = query.filter_by(domain=domain)
    if category:
        query = query.filter_by(category=category)
    if t_type:
        query = query.filter_by(transaction_type=t_type)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (Transaction.entity.like(term)) |
            (Transaction.reference.like(term)) |
            (Transaction.raw_sms.like(term))
        )

    transactions = query.order_by(Transaction.id.desc()).all()
    return jsonify({
        "count": len(transactions),
        "items": [t.to_dict() for t in transactions]
    })

@api_bp.post("/transactions")
def create_transaction():
    """Manually add or save an extracted transaction to the ledger."""
    data = request.get_json(silent=True) or {}
    is_valid, errors = validate_transaction(data)

    if not is_valid:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    normalized = normalize_transaction(data)

    existing = Transaction.query.filter_by(reference=normalized["reference"]).first()
    if existing:
        return jsonify({"error": "Transaction reference already exists", "item": existing.to_dict()}), 409

    txn = Transaction(
        reference=normalized["reference"],
        raw_sms=normalized.get("raw_sms", "Manual Entry"),
        domain=normalized["domain"],
        transaction_type=normalized["type"],
        entity=normalized["entity"],
        amount=normalized["amount"],
        fee=normalized["fee"],
        balance=normalized["balance"],
        category=normalized["category"],
        status=normalized["status"],
        date=normalized["date"],
        time=normalized["time"]
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({"status": "created", "item": txn.to_dict()}), 201

@api_bp.delete("/transactions/<int:txn_id>")
def delete_transaction(txn_id):
    """Delete a single transaction."""
    txn = Transaction.query.get_or_404(txn_id)
    db.session.delete(txn)
    db.session.commit()
    return jsonify({"status": "deleted", "id": txn_id})

@api_bp.delete("/transactions/reset")
def reset_ledger():
    """Clear all transactions from the ledger."""
    Transaction.query.delete()
    db.session.commit()
    return jsonify({"status": "reset", "message": "Ledger cleared successfully"})

@api_bp.get("/analytics")
def get_analytics():
    """Get Pandas financial profile for ledger."""
    transactions = Transaction.query.order_by(Transaction.id.asc()).all()
    profile = build_financial_profile(transactions)
    return jsonify(profile)

@api_bp.post("/insights")
def get_insights():
    """Ask AI advisor question on financial profile."""
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    transactions = Transaction.query.order_by(Transaction.id.asc()).all()
    profile = build_financial_profile(transactions)
    insight_text = model_service.generate_insight(profile, question)

    return jsonify({
        "question": question,
        "insight": insight_text,
        "profile_summary": {
            "income": profile.get("total_income"),
            "expenses": profile.get("total_expenses"),
            "cash_flow": profile.get("net_cash_flow"),
            "surplus_rate": profile.get("surplus_rate")
        }
    })

@api_bp.post("/sample-data")
def seed_sample_data():
    """Seed realistic African SME transaction SMS records into the database."""
    # Reset existing to present clean demo set
    Transaction.query.delete()

    sample_messages = [
        # Income / Sales
        "SAB8123XYZ Confirmed. You have received Ksh15,500.00 from JOHN MWANGI 254712345678 on 12/3/26 at 9:15 AM. New M-PESA balance is Ksh15,500.00. Fee Ksh0.00.",
        "RKD912384 Confirmed. You have received Ksh24,000.00 from MAMA ANITA CAFE 254722998877 on 13/3/26 at 2:30 PM. New M-PESA balance is Ksh39,500.00.",
        "QGH912301 Confirmed. You have received Ksh8,500.00 from WANJIKU WHOLESALERS on 14/3/26 at 11:00 AM. New M-PESA balance is Ksh48,000.00.",
        "TBF771239 Confirmed. You have received Ksh12,200.00 from JUMA TRADERS on 15/3/26 at 4:45 PM. New M-PESA balance is Ksh60,200.00.",

        # Expenses / Purchases
        "SAC994411 Confirmed. Ksh4,500.00 paid to NAIVAS SUPERMARKET on 12/3/26 at 1:10 PM. New M-PESA balance is Ksh11,000.00. Transaction cost, Ksh15.00.",
        "SAD112233 Confirmed. Ksh12,000.00 paid to QUICKMART WHOLESALE on 13/3/26 at 4:00 PM. New M-PESA balance is Ksh27,500.00. Transaction cost, Ksh25.00.",
        "SAE445566 Confirmed. Ksh3,200.00 paid to KPLC PREPAID for account 14229900 on 14/3/26 at 8:30 AM. New M-PESA balance is Ksh44,800.00. Transaction cost, Ksh10.00.",
        "SAF778899 Confirmed. Ksh500.00 bought Safaricom Airtime on 14/3/26 at 6:00 PM. New M-PESA balance is Ksh44,300.00.",
        "SAG110022 Confirmed. Ksh6,800.00 sent to RUBIS PETROL STATION for fuel on 15/3/26 at 7:20 AM. New M-PESA balance is Ksh37,500.00. Transaction cost, Ksh20.00.",
        "SAH334455 Confirmed. Ksh18,000.00 paid to KENYA MEAT DISTRIBUTORS on 16/3/26 at 10:15 AM. New M-PESA balance is Ksh19,500.00. Transaction cost, Ksh35.00.",

        # Banking & Overdraft
        "EQB992211 Equity Bank: You have transferred KES 5,000.00 to Account 01109283741 on 15/3/26 15:30. Available balance KES 35,400.00.",
        "FUL112233 Fuliza M-PESA: Outstanding amount is Ksh1,200.00. Repaid automatically from your deposit on 16/3/26.",
        "PCH556677 Pochi La Biashara: You have received Ksh4,200.00 from PETER OTIENO on 16/3/26 at 1:45 PM. Balance Ksh23,700.00."
    ]

    added = 0
    for sms in sample_messages:
        raw = model_service.extract_transaction(sms)
        norm = normalize_transaction(raw)
        txn = Transaction(
            reference=norm["reference"],
            raw_sms=sms,
            domain=norm["domain"],
            transaction_type=norm["type"],
            entity=norm["entity"],
            amount=norm["amount"],
            fee=norm["fee"],
            balance=norm["balance"],
            category=norm["category"],
            status=norm["status"],
            date=norm["date"],
            time=norm["time"]
        )
        db.session.add(txn)
        added += 1

    db.session.commit()
    return jsonify({
        "status": "success",
        "message": f"Successfully seeded {added} sample financial transactions into ledger.",
        "count": added
    }), 201

@api_bp.get("/export/csv")
def export_csv():
    """Export all ledger entries as CSV file."""
    transactions = Transaction.query.order_by(Transaction.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Transaction Reference", "Date", "Time", "Domain",
        "Transaction Type", "Category", "Entity / Merchant",
        "Amount (KES)", "Fee (KES)", "Balance (KES)", "Status", "Raw SMS"
    ])

    for t in transactions:
        writer.writerow([
            t.reference, t.date, t.time, t.domain,
            t.transaction_type, t.category, t.entity,
            t.amount, t.fee, t.balance, t.status, t.raw_sms
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=sme_ledger_export.csv"}
    )
