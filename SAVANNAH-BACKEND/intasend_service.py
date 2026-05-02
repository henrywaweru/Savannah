import os
import requests
import logging

logger = logging.getLogger(__name__)

INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY")
INTASEND_PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")

# Sandbox base URL — change to https://payment.intasend.com for live
BASE_URL = "https://sandbox.intasend.com"

def get_headers():
    return {
        "Authorization": f"Bearer {INTASEND_SECRET_KEY}",
        "Content-Type": "application/json",
    }

def stk_push(phone_number: str, amount: float, narrative: str = "Rent Payment") -> dict:
    """
    Send an STK push to the tenant's phone via Intasend.
    Phone must be in format 2547XXXXXXXX.
    """
    # Normalize phone
    phone = str(phone_number).strip()
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if phone.startswith("+"):
        phone = phone[1:]

    url = f"{BASE_URL}/api/v1/payment/mpesa-stk-push/"
    payload = {
        "phone_number": phone,
        "amount": int(amount),  # Intasend requires integer
        "narrative": narrative,
        "api_ref": f"SAV-{phone[-4:]}",
    }

    logger.info("Intasend STK push: phone=%s, amount=%s", phone, amount)

    try:
        response = requests.post(url, json=payload, headers=get_headers(), timeout=30)
        data = response.json()
        logger.info("Intasend STK response: %s", data)
        return data
    except Exception as e:
        logger.error("Intasend STK push error: %s", str(e))
        raise

def check_payment_status(invoice_id: str) -> dict:
    """
    Check the status of a payment using its invoice ID.
    """
    url = f"{BASE_URL}/api/v1/payment/status/{invoice_id}/"
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        data = response.json()
        logger.info("Intasend status check: invoice=%s, response=%s", invoice_id, data)
        return data
    except Exception as e:
        logger.error("Intasend status check error: %s", str(e))
        raise
