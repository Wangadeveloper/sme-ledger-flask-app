import unittest
from config import Config
from app import create_app
from app.models import db
from app.models.transaction import Transaction
from app.services.model_service import ModelService
from app.services.validation_service import validate_transaction, normalize_transaction
from app.services.analytics_service import build_financial_profile

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

class TestSMELedger(unittest.TestCase):

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.model_service = ModelService()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_health_endpoint(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "sme-ledger")

    def test_mpesa_income_extraction(self):
        sms = "SAB8123XYZ Confirmed. You have received Ksh15,500.00 from JOHN MWANGI on 12/3/26 at 9:15 AM. New M-PESA balance is Ksh15,500.00."
        extracted = self.model_service.extract_transaction(sms)
        self.assertEqual(extracted["reference"], "SAB8123XYZ")
        self.assertEqual(extracted["amount"], 15500.0)
        self.assertEqual(extracted["type"], "income")
        self.assertEqual(extracted["entity"], "John Mwangi")
        self.assertEqual(extracted["balance"], 15500.0)

    def test_paybill_expense_extraction(self):
        sms = "SAC994411 Confirmed. Ksh4,500.00 paid to NAIVAS SUPERMARKET on 12/3/26 at 1:10 PM. New M-PESA balance is Ksh11,000.00. Transaction cost, Ksh15.00."
        extracted = self.model_service.extract_transaction(sms)
        self.assertEqual(extracted["reference"], "SAC994411")
        self.assertEqual(extracted["amount"], 4500.0)
        self.assertEqual(extracted["type"], "expense")
        self.assertEqual(extracted["entity"], "Naivas Supermarket")
        self.assertEqual(extracted["category"], "food")
        self.assertEqual(extracted["fee"], 15.0)

    def test_validation_and_normalization(self):
        valid_payload = {
            "reference": "TXN123456",
            "amount": "1250.50",
            "type": "EXPENSE",
            "domain": "MPESA",
            "entity": "  quickmart supermarket  ",
            "category": "FOOD"
        }
        is_valid, errors = validate_transaction(valid_payload)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        norm = normalize_transaction(valid_payload)
        self.assertEqual(norm["reference"], "TXN123456")
        self.assertEqual(norm["amount"], 1250.50)
        self.assertEqual(norm["type"], "expense")
        self.assertEqual(norm["domain"], "mpesa")
        self.assertEqual(norm["entity"], "Quickmart Supermarket")
        self.assertEqual(norm["category"], "food")

    def test_pandas_analytics(self):
        txns = [
            {"amount": 20000.0, "type": "income", "category": "sales", "entity": "Customer A", "balance": 20000.0, "date": "2026-03-15"},
            {"amount": 5000.0, "type": "expense", "category": "food", "entity": "Supermarket", "balance": 15000.0, "date": "2026-03-15"},
            {"amount": 3000.0, "type": "expense", "category": "utilities", "entity": "KPLC", "balance": 12000.0, "date": "2026-03-16"},
        ]
        profile = build_financial_profile(txns)
        self.assertEqual(profile["total_income"], 20000.0)
        self.assertEqual(profile["total_expenses"], 8000.0)
        self.assertEqual(profile["net_cash_flow"], 12000.0)
        self.assertEqual(profile["surplus_rate"], 60.0)
        self.assertEqual(profile["financial_health_signals"]["health_rating"], "Strong Surplus")

    def test_sample_data_seeding_and_analytics_api(self):
        # 1. Seed sample data
        seed_res = self.client.post("/api/sample-data")
        self.assertEqual(seed_res.status_code, 201)

        # 2. Get transactions list
        list_res = self.client.get("/api/transactions")
        self.assertEqual(list_res.status_code, 200)
        items = list_res.get_json()["items"]
        self.assertGreater(len(items), 10)

        # 3. Analytics endpoint
        ana_res = self.client.get("/api/analytics")
        self.assertEqual(ana_res.status_code, 200)
        profile = ana_res.get_json()
        self.assertGreater(profile["total_income"], 0)
        self.assertGreater(profile["total_expenses"], 0)

        # 4. Insights AI endpoint
        ins_res = self.client.post("/api/insights", json={"question": "What is my cash flow?"})
        self.assertEqual(ins_res.status_code, 200)
        self.assertIn("Cash Flow Overview", ins_res.get_json()["insight"])

        # 5. CSV Export endpoint
        csv_res = self.client.get("/api/export/csv")
        self.assertEqual(csv_res.status_code, 200)
        self.assertEqual(csv_res.mimetype, "text/csv")
        self.assertIn("SAB8123XYZ", csv_res.get_data(as_text=True))

if __name__ == "__main__":
    unittest.main()
