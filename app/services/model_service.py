"""Model service for transaction extraction and AI financial guidance.

Dual-engine architecture:
1. GGUF Llama-CPP Model Loader (Auto-detects models/sme-ledger-v2-Q4_K_M.gguf when available)
2. Fast Rule-based / Regex NLP Extractor (Fallback & 0-RAM safety net)
"""

import os
import re
import json
import random
import urllib.request
from datetime import datetime

DEFAULT_MODEL_URL = "https://huggingface.co/EngineerWanga0791709020/SME-Ledger/resolve/main/sme-ledger-v2-Q4_K_M.gguf"

class ModelService:
    def __init__(self, model_path: str = None, model_url: str = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        default_model = os.path.join(base_dir, "models", "sme-ledger-v2-Q4_K_M.gguf")
        
        self.model_path = model_path or os.getenv("MODEL_PATH", default_model)
        self.model_url = model_url or os.getenv("MODEL_URL", DEFAULT_MODEL_URL)
        self.engine = os.getenv("MODEL_ENGINE", "auto").lower()
        self._llm = None
        self._tried_load = False

    def download_model_if_missing(self) -> bool:
        """Check if model exists in model folder, download from Hugging Face if missing."""
        if os.path.exists(self.model_path) and os.path.getsize(self.model_path) > 0:
            print(f"[ModelService] GGUF model exists at '{self.model_path}'.")
            return True

        model_dir = os.path.dirname(self.model_path)
        if model_dir:
            os.makedirs(model_dir, exist_ok=True)

        print(f"[ModelService] GGUF model file not found at '{self.model_path}'.")
        print(f"[ModelService] Downloading model from Hugging Face ({self.model_url})...")

        try:
            req = urllib.request.Request(
                self.model_url,
                headers={"User-Agent": "Mozilla/5.0 (SME-Ledger-Downloader)"}
            )
            temp_path = self.model_path + ".tmp"
            
            with urllib.request.urlopen(req) as response, open(temp_path, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                block_size = 1024 * 1024  # 1 MB chunk

                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    out_file.write(buffer)
                    downloaded += len(buffer)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        mb_dn = downloaded / (1024 * 1024)
                        mb_tot = total_size / (1024 * 1024)
                        if (downloaded // block_size) % 10 == 0 or percent == 100:
                            print(f"[ModelService] Downloading: {mb_dn:.1f} MB / {mb_tot:.1f} MB ({percent}%)", flush=True)

            os.rename(temp_path, self.model_path)
            print(f"[ModelService] Model successfully downloaded to '{self.model_path}'!")
            return True
        except Exception as e:
            print(f"[ModelService] Failed to download GGUF model: {e}")
            if os.path.exists(self.model_path + ".tmp"):
                try:
                    os.remove(self.model_path + ".tmp")
                except Exception:
                    pass
            return False

    def load(self):
        """Lazy load GGUF model if available (downloads from HF if missing)."""
        if self._tried_load:
            return self._llm

        self._tried_load = True

        # Check and download model if missing
        self.download_model_if_missing()

        if not os.path.exists(self.model_path):
            print(f"[ModelService] GGUF model file not available at '{self.model_path}'. Using NLP extractor engine.")
            self.engine = "fallback"
            return None

        try:
            from llama_cpp import Llama
            print(f"[ModelService] Loading GGUF model from '{self.model_path}'...")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=min(4, max(1, os.cpu_count() or 1)),
                verbose=False
            )
            self.engine = "llama_cpp"
            print(f"[ModelService] Successfully loaded GGUF model!")
        except Exception as e:
            print(f"[ModelService] Could not initialize llama_cpp: {e}. Falling back to NLP extractor.")
            self._llm = None
            self.engine = "fallback"

        return self._llm

    def extract_transaction(self, sms: str) -> dict:
        """Extract structured financial data from raw SMS text using GGUF model or NLP fallback."""
        if not sms or not sms.strip():
            return {}

        llm = self.load()

        # Try GGUF Model Inference if loaded
        if llm is not None:
            try:
                prompt = (
                    f"<start_of_turn>user\n"
                    f"Extract structured financial JSON from this SMS:\n{sms}\n"
                    f"<end_of_turn>\n<start_of_turn>model\n"
                )
                response = llm(
                    prompt,
                    max_tokens=256,
                    stop=["<end_of_turn>", "<|im_end|>"],
                    temperature=0.1
                )
                output_text = response["choices"][0]["text"].strip()
                
                # Extract JSON substring
                json_match = re.search(r"\{.*\}", output_text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    parsed["raw_sms"] = sms.strip()
                    return parsed
            except Exception as e:
                print(f"[ModelService] GGUF model inference error ({e}). Using NLP extractor.")

        return self._extract_regex(sms)

    def _extract_regex(self, sms: str) -> dict:
        """High-precision regex parser for M-Pesa, Bank, and Mobile Money transaction SMS."""
        sms_clean = sms.strip()
        sms_lower = sms_clean.lower()

        # 1. Reference Code Extraction
        ref_match = re.search(r"\b([A-Z0-9]{8,12})\b", sms_clean)
        reference = ref_match.group(1) if ref_match else f"TXN{random.randint(100000, 999999)}"

        # 2. Amount Extraction
        amount_match = re.search(r"(?:Ksh|KES|USD|EUR)\s*([0-9,]+(?:\.[0-9]{1,2})?)", sms_clean, re.IGNORECASE)
        amount = 0.0
        if amount_match:
            try:
                amount = float(amount_match.group(1).replace(",", ""))
            except ValueError:
                amount = 0.0

        # 3. Balance Extraction
        balance_match = re.search(r"(?:balance|bal|available balance)(?:\s+is|\s+was)?\s*(?:Ksh|KES)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", sms_clean, re.IGNORECASE)
        balance = 0.0
        if balance_match:
            try:
                balance = float(balance_match.group(1).replace(",", ""))
            except ValueError:
                balance = 0.0

        # 4. Fee Extraction
        fee_match = re.search(r"(?:cost|fee|charge)[,\s]*(?:is|was)?\s*(?:Ksh|KES)\s*([0-9,]+(?:\.[0-9]{1,2})?)", sms_clean, re.IGNORECASE)
        fee = 0.0
        if fee_match:
            try:
                fee = float(fee_match.group(1).replace(",", ""))
            except ValueError:
                fee = 0.0

        # 5. Date & Time Extraction
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M:%S")

        date_match = re.search(r"(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})", sms_clean)
        if date_match:
            raw_d = date_match.group(1).replace(".", "/").replace("-", "/")
            parts = raw_d.split("/")
            if len(parts) == 3:
                day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
                if len(year) == 2:
                    year = "20" + year
                date_str = f"{year}-{month}-{day}"

        time_match = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)", sms_clean, re.IGNORECASE)
        if time_match:
            time_str = time_match.group(1)

        # 6. Domain Detection
        domain = "mpesa"
        if "paybill" in sms_lower:
            domain = "paybill"
        elif "buy goods" in sms_lower or "till" in sms_lower:
            domain = "till"
        elif "pochi" in sms_lower:
            domain = "pochi"
        elif "fuliza" in sms_lower:
            domain = "fuliza"
        elif "airtime" in sms_lower:
            domain = "airtime"
        elif any(bank in sms_lower for bank in ["equity", "kcb", "co-op", "mco-opcash", "ncba", "stanbic", "absa", "bank"]):
            domain = "banking"

        # 7. Direction / Transaction Type
        t_type = "expense"
        if any(term in sms_lower for term in ["received", "credited", "deposit", "you have received"]):
            t_type = "income"
        elif "fuliza" in sms_lower:
            t_type = "fuliza"
        elif any(term in sms_lower for term in ["withdraw", "withdrawn"]):
            t_type = "withdrawal"
        elif any(term in sms_lower for term in ["reversal", "reversed"]):
            t_type = "reversal"
        elif any(term in sms_lower for term in ["sent to", "paid to", "bought", "transferred"]):
            t_type = "expense"

        # 8. Entity Extraction
        entity = "Unknown Entity"
        entity_patterns = [
            r"paid to\s+([A-Za-z0-9\s\.\,\'-]+?)(?=\s+on|\s+for|\s+Ksh|\s+KES|\.|$)",
            r"sent to\s+([A-Za-z0-9\s\.\,\'-]+?)(?=\s+\d|\s+on|\s+Ksh|\s+KES|\.|$)",
            r"received\s+Ksh[0-9,\.]+\s+from\s+([A-Za-z0-9\s\.\,\'-]+?)(?=\s+on|\s+Ksh|\.|$)",
            r"from\s+([A-Za-z0-9\s\.\,\'-]+?)(?=\s+on|\s+at|\s+Ksh|\.|$)",
            r"bought\s+([A-Za-z0-9\s\.\,\'-]+?)(?=\s+of|\s+on|\s+Ksh|\.|$)",
            r"to\s+([A-Za-z0-9\s\.\,\'-]+?)(?=\s+on|\s+Ksh|\.|$)"
        ]
        for pat in entity_patterns:
            m = re.search(pat, sms_clean, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                extracted = re.sub(r"\b(Ksh|KES|new|balance|is|was|on|at|ref|acc)\b.*$", "", extracted, flags=re.IGNORECASE).strip()
                if len(extracted) > 2 and len(extracted) < 40:
                    entity = extracted.title()
                    break

        if entity == "Unknown Entity":
            if "safaricom" in sms_lower or "airtime" in sms_lower:
                entity = "Safaricom Airtime"
            elif "kplc" in sms_lower:
                entity = "KPLC Prepaid"
            elif "naivas" in sms_lower:
                entity = "Naivas Supermarket"
            elif "quickmart" in sms_lower:
                entity = "Quickmart Supermarket"
            elif "equity" in sms_lower:
                entity = "Equity Bank"
            elif "kcb" in sms_lower:
                entity = "KCB Bank"
            elif "fuliza" in sms_lower:
                entity = "NCBA Fuliza"

        # 9. Category Auto-classification
        category = "other"
        entity_lower = entity.lower()
        if t_type == "income":
            category = "sales"
        elif any(k in entity_lower or k in sms_lower for k in ["naivas", "quickmart", "carrefour", "supermarket", "food", "restaurant", "cafe", "butchery"]):
            category = "food"
        elif any(k in entity_lower or k in sms_lower for k in ["kplc", "water", "internet", "zuku", "safaricom home", "rent", "token"]):
            category = "utilities"
        elif any(k in entity_lower or k in sms_lower for k in ["wholesaler", "distributor", "stock", "hardware", "supplies", "inventory"]):
            category = "inventory"
        elif any(k in entity_lower or k in sms_lower for k in ["fuel", "total", "rubis", "uber", "bolt", "matatu", "fare", "transport"]):
            category = "transport"
        elif any(k in entity_lower or k in sms_lower for k in ["airtime", "bundles", "data"]):
            category = "services"
        elif any(k in entity_lower or k in sms_lower for k in ["salary", "wages", "casual"]):
            category = "salary"
        elif t_type in ["fuliza", "loan"]:
            category = "loans"
        elif t_type == "transfer":
            category = "transfers"

        return {
            "transaction_id": reference,
            "reference": reference,
            "raw_sms": sms_clean,
            "domain": domain,
            "type": t_type,
            "entity": entity,
            "amount": amount,
            "fee": fee,
            "balance": balance,
            "category": category,
            "status": "completed",
            "date": date_str,
            "time": time_str
        }

    def generate_insight(self, profile: dict, question: str) -> str:
        """Deterministic financial advisor logic providing actionable insights for SMEs."""
        if not profile or profile.get("transaction_count", 0) == 0:
            return "No transactions found in your ledger yet. Upload or extract transaction SMS messages to generate financial insights."

        llm = self.load()
        q = (question or "").lower()
        income = profile.get("total_income", 0.0)
        expenses = profile.get("total_expenses", 0.0)
        cash_flow = profile.get("net_cash_flow", 0.0)
        surplus_rate = profile.get("surplus_rate", 0.0)
        top_cats = profile.get("top_spending_categories", {})
        top_merchants = profile.get("top_spending_entities", {})
        signals = profile.get("financial_health_signals", {})

        # If LLM model is loaded, we can pass financial summary to GGUF model for natural generation
        if llm is not None:
            try:
                context_str = f"SME Profile: Income=KES {income}, Expenses=KES {expenses}, Net Cash Flow=KES {cash_flow}, Surplus={surplus_rate}%."
                prompt = (
                    f"<start_of_turn>user\n"
                    f"You are an SME Financial Advisor. Context: {context_str}\n"
                    f"User Question: {question}\n"
                    f"<end_of_turn>\n<start_of_turn>model\n"
                )
                response = llm(prompt, max_tokens=200, stop=["<end_of_turn>"], temperature=0.3)
                output = response["choices"][0]["text"].strip()
                if len(output) > 20:
                    return output
            except Exception as e:
                print(f"[ModelService] LLM insight generation error ({e}). Using deterministic insights.")

        if "cash flow" in q or "summary" in q or "performance" in q:
            status_text = "positive and healthy" if cash_flow > 0 else "in deficit (expenses exceed income)"
            return (
                f"📊 **Cash Flow Overview**:\n\n"
                f"- **Total Income**: KES {income:,.2f}\n"
                f"- **Total Expenses**: KES {expenses:,.2f}\n"
                f"- **Net Cash Flow**: KES {cash_flow:,.2f} ({status_text})\n"
                f"- **Surplus Rate**: {surplus_rate:.1f}%\n\n"
                f"**Recommendation**: " +
                ("Maintain a 20%+ cash buffer in your wallet/bank for unexpected operational costs." if surplus_rate >= 20
                 else "Your surplus is tight. Review top spending categories to reduce overhead.")
            )

        elif "spend" in q or "category" in q or "expense" in q or "where" in q:
            cats_formatted = "\n".join([f"- **{cat.title()}**: KES {amt:,.2f}" for cat, amt in list(top_cats.items())[:3]])
            merch_formatted = "\n".join([f"- **{ent}**: KES {amt:,.2f}" for ent, amt in list(top_merchants.items())[:3]])
            return (
                f"💳 **Spending Analysis**:\n\n"
                f"**Top Expense Categories**:\n{cats_formatted if cats_formatted else '- No categories logged.'}\n\n"
                f"**Top Payees / Merchants**:\n{merch_formatted if merch_formatted else '- No merchants logged.'}\n\n"
                f"💡 *Tip*: Negotiate bulk rates with your top vendors or transition to digital till payments for lower transaction fees."
            )

        elif "loan" in q or "credit" in q or "fuliza" in q or "afford" in q:
            debt_alert = signals.get("fuliza_debt_alert", False)
            return (
                f"🏦 **Credit & Health Assessment**:\n\n"
                f"- **Health Rating**: {signals.get('health_rating', 'Good')}\n"
                f"- **Surplus Buffer**: {surplus_rate:.1f}%\n"
                f"- **Overdraft / Fuliza Warning**: {'⚠️ Active debt/fuliza usage detected' if debt_alert else '✅ No active overdraft debt'}\n\n"
                f"**Credit Advice**: " +
                ("You qualify for working capital financing based on positive cash flow." if surplus_rate > 15 and not debt_alert
                 else "Clear outstanding Fuliza/overdraft debts before applying for micro-loans to improve your credit terms.")
            )

        else:
            return (
                f"💡 **SME Financial Advisory**:\n\n"
                f"Based on {profile.get('transaction_count', 0)} logged transactions:\n"
                f"- Net Balance/Cash Flow: **KES {cash_flow:,.2f}**\n"
                f"- Top Expense: **{list(top_cats.keys())[0].title() if top_cats else 'N/A'}**\n"
                f"- Operational Buffer: **{surplus_rate:.1f}%**\n\n"
                f"You can ask me about cash flow summaries, spending breakdowns, loan readiness, or cost reduction strategies."
            )
