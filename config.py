import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    MODEL_PATH = os.getenv(
        "MODEL_PATH",
        os.path.join(BASE_DIR, "models", "sme-ledger-v2-Q4_K_M.gguf"),
    )
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "sme_ledger.db"),
    )
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", DATABASE_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
