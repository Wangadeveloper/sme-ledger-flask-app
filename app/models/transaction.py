from datetime import datetime, timezone
from app.models import db

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), unique=True, nullable=False, index=True)
    raw_sms = db.Column(db.Text, nullable=True)
    domain = db.Column(db.String(50), nullable=False, default="mpesa") # mpesa, banking, pochi, paybill, till, airtime
    transaction_type = db.Column(db.String(20), nullable=False, default="expense") # income, expense, transfer, fuliza, loan, reversal, withdrawal
    entity = db.Column(db.String(120), nullable=False) # Merchant, Sender, Receiver, Bank
    amount = db.Column(db.Float, nullable=False, default=0.0)
    fee = db.Column(db.Float, nullable=False, default=0.0)
    balance = db.Column(db.Float, nullable=False, default=0.0)
    category = db.Column(db.String(50), nullable=False, default="other") # food, utilities, inventory, salary, transport, sales, transfers, services, loans
    status = db.Column(db.String(20), nullable=False, default="completed") # completed, failed, reversed, pending
    date = db.Column(db.String(20), nullable=True) # YYYY-MM-DD
    time = db.Column(db.String(20), nullable=True) # HH:MM:SS
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "reference": self.reference,
            "raw_sms": self.raw_sms,
            "domain": self.domain,
            "type": self.transaction_type,
            "transaction_type": self.transaction_type,
            "entity": self.entity,
            "amount": self.amount,
            "fee": self.fee,
            "balance": self.balance,
            "category": self.category,
            "status": self.status,
            "date": self.date,
            "time": self.time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
