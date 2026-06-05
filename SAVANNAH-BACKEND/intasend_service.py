import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

logger = logging.getLogger(__name__)

BASE_URL = "https://sandbox.intasend.com"

def get_headers():
    key = os.getenv("INTASEND_SECRET_KEY")
    logger.info("Using Intasend key: %s", key[:20] if key else "MISSING")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

def stk_push(phone_number: str, amount: float, narrative: str = "Rent Payment") -> dict:
    phone = str(phone_number).strip()
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if phone.startswith("+"):
        phone = phone[1:]

    url = f"{BASE_URL}/api/v1/payment/mpesa-stk-push/"
    payload = {
        "phone_number": phone,
        "amount": int(amount),
        "narrative": narrative,
        "api_ref": f"SAV-{phone[-4:]}",
    }

    logger.info("Intasend STK push: phone=%s, amount=%s", phone, amount)

    try:
        response = requests.post(url, json=payload, headers=get_headers(), timeout=30)
        logger.info("Intasend raw response: status=%s body=%s", response.status_code, response.text[:300])

        if not response.text.strip():
            raise Exception("Empty response from Intasend")

        data = response.json()
        return data
    except requests.exceptions.JSONDecodeError:
        logger.error("Intasend returned non-JSON: %s", response.text[:200])
        raise Exception(f"Intasend error: {response.text[:200]}")
    except Exception as e:
        logger.error("Intasend STK push error: %s", str(e))
        raise

def check_payment_status(invoice_id: str) -> dict:
    url = f"{BASE_URL}/api/v1/payment/status/{invoice_id}/"
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        if not response.text.strip():
            return {"state": "PENDING"}
        return response.json()
    except Exception as e:
        logger.error("Intasend status check error: %s", str(e))
        raise
