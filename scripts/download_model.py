#!/usr/bin/env python3
"""Standalone script to check and download the GGUF model from Hugging Face if missing."""
import os
import sys

# Ensure project root is on Python path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.model_service import ModelService

def main():
    print("Checking GGUF model file status...")
    service = ModelService()
    success = service.download_model_if_missing()
    if success and os.path.exists(service.model_path):
        print(f"Model ready at: {service.model_path}")
    else:
        print("Model file unavailable. App will use regex/NLP fallback engine.")

if __name__ == "__main__":
    main()
