from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from intasend_service import stk_push as intasend_stk_push, check_payment_status as intasend_check_status
from typing import Optional, List
import os
import jwt
import hashlib
import json
from datetime import datetime, timedelta
import logging
import random
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Savannah Property Management API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set in environment. Add it to your .env file.")
ALGORITHM = "HS256"
security = HTTPBearer()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["savannah_pms"]

users_col = db["users"]
properties_col = db["properties"]
units_col = db["units"]
transactions_col = db["transactions"]
pending_transactions_col = db["pending_transactions"]

# Ensure basic indexes exist
users_col.create_index("email", unique=True)
properties_col.create_index("id", unique=True)
units_col.create_index("id", unique=True)
transactions_col.create_index("id", unique=True)
pending_transactions_col.create_index("checkout_request_id", unique=True)

# Seed initial data if collections are empty
if users_col.count_documents({}) == 0:
    users_col.insert_many([
        {
            "id": 1,
            "name": "Admin Manager",
            "role": "admin",
            "email": "admin@savannah.co.ke",
            "password": hashlib.sha256("admin123".encode()).hexdigest()
        },
        {
            "id": 2,
            "name": "Jane Wanjiku",
            "role": "accountant",
            "email": "accountant@savannah.co.ke",
            "password": hashlib.sha256("account123".encode()).hexdigest()
        },
        {
            "id": 3,
            "name": "James Mwangi",
            "role": "tenant",
            "unit": "A-101",
            "email": "tenant001@savannah.co.ke",
            "password": hashlib.sha256("tenant123".encode()).hexdigest()
        },
    ])

if properties_col.count_documents({}) == 0:
    properties_col.insert_many([
        {"id": 1, "name": "Savannah Heights", "location": "Westlands, Nairobi", "total_units": 120, "occupied": 108},
        {"id": 2, "name": "Acacia Courts",    "location": "Kilimani, Nairobi",  "total_units": 95,  "occupied": 89},
        {"id": 3, "name": "Baobab Residences","location": "Karen, Nairobi",     "total_units": 85,  "occupied": 72},
    ])

if units_col.count_documents({}) == 0:
    units_col.insert_many([
        {"id": 1, "property_id": 1, "unit_number": "A-101", "rent_amount": 35000, "status": "Occupied",  "tenant": "James Mwangi",    "balance": 0},
        {"id": 2, "property_id": 1, "unit_number": "A-102", "rent_amount": 35000, "status": "Occupied",  "tenant": "Mary Njoroge",    "balance": 35000},
        {"id": 3, "property_id": 1, "unit_number": "B-201", "rent_amount": 42000, "status": "Occupied",  "tenant": "Peter Kamau",     "balance": 0},
        {"id": 4, "property_id": 1, "unit_number": "B-202", "rent_amount": 42000, "status": "Vacant",    "tenant": None,              "balance": 0},
        {"id": 5, "property_id": 2, "unit_number": "C-301", "rent_amount": 55000, "status": "Occupied",  "tenant": "Grace Achieng",   "balance": 55000},
        {"id": 6, "property_id": 2, "unit_number": "C-302", "rent_amount": 55000, "status": "Occupied",  "tenant": "David Otieno",    "balance": 0},
        {"id": 7, "property_id": 3, "unit_number": "D-401", "rent_amount": 75000, "status": "Occupied",  "tenant": "Sarah Muthoni",   "balance": 75000},
        {"id": 8, "property_id": 3, "unit_number": "D-402", "rent_amount": 75000, "status": "Maintenance","tenant": None,             "balance": 0},
    ])

if transactions_col.count_documents({}) == 0:
    transactions_col.insert_many([
        {"id": "TXN-001", "tenant": "James Mwangi",  "unit": "A-101", "amount": 35000, "method": "M-Pesa",       "status": "Completed", "date": "2025-04-05", "ref": "QHF2K8J9"},
        {"id": "TXN-002", "tenant": "Peter Kamau",    "unit": "B-201", "amount": 42000, "method": "Bank Transfer", "status": "Completed", "date": "2025-04-03", "ref": "BTR884K2"},
        {"id": "TXN-003", "tenant": "David Otieno",   "unit": "C-302", "amount": 55000, "method": "Airtel Money",  "status": "Completed", "date": "2025-04-07", "ref": "AMX77P1Q"},
        {"id": "TXN-004", "tenant": "Mary Njoroge",   "unit": "A-102", "amount": 35000, "method": "M-Pesa",       "status": "Pending",   "date": "2025-04-10", "ref": "QHF4T9R2"},
        {"id": "TXN-005", "tenant": "Grace Achieng",  "unit": "C-301", "amount": 55000, "method": "Card",         "status": "Failed",    "date": "2025-04-09", "ref": "CRD992XZ"},
        {"id": "TXN-006", "tenant": "Sarah Muthoni",  "unit": "D-401", "amount": 75000, "method": "M-Pesa",       "status": "Pending",   "date": "2025-04-11", "ref": "QHF7M3N8"},
    ])


def serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


def serialize_docs(cursor):
    return [serialize_doc(doc) for doc in cursor]


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_next_user_id() -> int:
    last = users_col.find_one(sort=[("id", -1)])
    return (last["id"] if last else 0) + 1


def get_next_transaction_id() -> str:
    # Extract numeric part from all IDs and find the max — avoids lexicographic sort bug
    max_num = 0
    for doc in transactions_col.find({}, {"id": 1}):
        try:
            num = int(str(doc.get("id", "0")).split("-")[-1])
            if num > max_num:
                max_num = num
        except Exception:
            pass
    return f"TXN-{max_num + 1:03d}"

# ─── Auth ────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "tenant"

def create_token(user_data: dict) -> str:
    payload = {**user_data, "exp": datetime.utcnow() + timedelta(hours=8)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/auth/login")
def login(req: LoginRequest):
    email = normalize_email(req.email)
    logger.info("Login attempt for email=%s", email)
    user = users_col.find_one({"email": email})
    if not user:
        logger.info("Login failed: user not found %s", email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expected_password = hashlib.sha256(req.password.encode()).hexdigest()
    if user.get("password") != expected_password:
        logger.info("Login failed: invalid password for %s", email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info("Login success for %s", email)
    token_data = {"id": user["id"], "name": user["name"], "email": email, "role": user["role"]}
    return {"token": create_token(token_data), "user": token_data}

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    email = normalize_email(req.email)
    name = req.name.strip()
    password = req.password
    role = "tenant"

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    if users_col.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    new_id = get_next_user_id()
    user_record = {
        "id": new_id,
        "name": name,
        "role": role,
        "unit": "Pending Assignment",
        "email": email,
        "password": hashlib.sha256(password.encode()).hexdigest(),
    }
    users_col.insert_one(user_record)

    token_data = {"id": new_id, "name": name, "email": email, "role": role}
    return {
        "success": True,
        "message": "Account created successfully",
        "token": create_token(token_data),
        "user": token_data,
    }

# ─── Dashboard Stats ─────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
def get_stats(user=Depends(verify_token)):
    total_units = sum(p["total_units"] for p in properties_col.find({}))
    occupied = sum(p["occupied"] for p in properties_col.find({}))
    expected_revenue = sum(u["rent_amount"] for u in units_col.find({"status": "Occupied"}))
    collected = sum(t["amount"] for t in transactions_col.find({"status": "Completed"}))
    arrears_count = units_col.count_documents({"balance": {"$gt": 0}, "status": "Occupied"})
    return {
        "total_units": total_units,
        "occupied_units": occupied,
        "vacant_units": total_units - occupied,
        "occupancy_rate": round((occupied / total_units) * 100, 1) if total_units else 0,
        "expected_revenue": expected_revenue,
        "collected_revenue": collected,
        "collection_rate": round((collected / expected_revenue) * 100, 1) if expected_revenue else 0,
        "tenants_in_arrears": arrears_count,
        "total_properties": properties_col.count_documents({}),
    }

@app.get("/api/dashboard/monthly-collections")
def monthly_collections(user=Depends(verify_token)):
    # Compute expected revenue from occupied units (static per month)
    expected = sum(u["rent_amount"] for u in units_col.find({"status": "Occupied"}))

    # Aggregate completed transactions by month from real data
    collected_by_month = {}
    for txn in transactions_col.find({"status": "Completed"}):
        date_str = txn.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            key = dt.strftime("%b %Y")  # e.g. "Apr 2025"
            collected_by_month[key] = collected_by_month.get(key, 0) + txn.get("amount", 0)
        except Exception:
            pass

    # Build last 6 months in order
    from datetime import date
    from dateutil.relativedelta import relativedelta
    result = []
    today = date.today()
    for i in range(5, -1, -1):
        month_dt = today - relativedelta(months=i)
        label = month_dt.strftime("%b")
        key = month_dt.strftime("%b %Y")
        result.append({
            "month": label,
            "collected": collected_by_month.get(key, 0),
            "expected": expected,
        })
    return result

# ─── Properties ──────────────────────────────────────────────────────────
@app.get("/api/properties")
def get_properties(user=Depends(verify_token)):
    return serialize_docs(properties_col.find({}))

# ─── Units ───────────────────────────────────────────────────────────────
@app.get("/api/units")
def get_units(user=Depends(verify_token)):
    return serialize_docs(units_col.find({}))

# ─── Transactions ─────────────────────────────────────────────────────────
@app.get("/api/transactions")
def get_transactions(user=Depends(verify_token)):
    return serialize_docs(transactions_col.find({}))

class PaymentRequest(BaseModel):
    unit_id: int
    amount: float
    method: str
    tenant_name: str

# M-Pesa Payment Request Model
class MpesaPaymentRequest(BaseModel):
    tenant_id: int
    amount: float
    phone_number: str
    property_id: int

@app.post("/api/payments/initiate")
def initiate_payment(req: PaymentRequest, user=Depends(verify_token)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")
    if req.amount > 10_000_000:
        raise HTTPException(status_code=400, detail="Payment amount exceeds maximum allowed")
    if not req.tenant_name or not req.tenant_name.strip():
        raise HTTPException(status_code=400, detail="Tenant name is required")
    logger.info("Initiate payment request: user=%s, unit_id=%s, amount=%s, method=%s, tenant=%s", user.get("email"), req.unit_id, req.amount, req.method, req.tenant_name)
    ref = "FLW-" + "".join([str(random.randint(0,9)) for _ in range(8)])
    unit_doc = units_col.find_one({"id": req.unit_id})

    if not unit_doc:
        logger.warning("Payment initiate: unit_id not found: %s", req.unit_id)

    unit_number = unit_doc["unit_number"] if unit_doc else "N/A"
    balance = max(0, (unit_doc.get("balance", 0) if unit_doc else 0) - req.amount)

    new_txn = {
        "id": get_next_transaction_id(),
        "tenant": req.tenant_name,
        "unit": unit_number,
        "amount": req.amount,
        "method": req.method,
        "status": "Completed",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "ref": ref,
    }
    transactions_col.insert_one(new_txn)

    if unit_doc:
        units_col.update_one({"id": req.unit_id}, {"$set": {"balance": balance}})
    else:
        logger.warning("Payment recorded but unit not updated because unit_doc is missing")

    logger.info("Payment recorded: %s", new_txn)
    return {"success": True, "transaction": new_txn, "message": f"Payment of KES {req.amount:,.0f} recorded successfully"}

# ─── Tenants in Arrears ───────────────────────────────────────────────────
@app.get("/api/arrears")
def get_arrears(user=Depends(verify_token)):
    return serialize_docs(units_col.find({"balance": {"$gt": 0}, "status": "Occupied"}))


# Intasend payment service loaded from intasend_service.py
# ========== ENDPOINT 1: Initiate STK Push (Intasend) ==========
@app.post("/api/mpesa/stkpush")
async def initiate_mpesa_payment(
    payment_data: MpesaPaymentRequest,
    current_user: dict = Depends(verify_token)
):
    try:
        if payment_data.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero")

        phone = str(payment_data.phone_number).strip()
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        logger.info("Intasend STK push: tenant_id=%s, amount=%s, phone=%s",
                    payment_data.tenant_id, payment_data.amount, phone)

        result = intasend_stk_push(
            phone_number=phone,
            amount=payment_data.amount,
            narrative=f"Rent Payment - SAV{payment_data.tenant_id}"
        )

        # Intasend returns invoice object on success
        invoice_id = result.get("invoice", {}).get("invoice_id") or result.get("id")
        state = result.get("invoice", {}).get("state") or result.get("state", "")

        if invoice_id:
            pending_transactions_col.insert_one({
                "checkout_request_id": invoice_id,
                "tenant_id": payment_data.tenant_id,
                "amount": payment_data.amount,
                "property_id": payment_data.property_id,
                "phone": phone,
                "status": "pending",
                "created_at": datetime.now()
            })

            logger.info("STK push sent: invoice_id=%s", invoice_id)
            return {
                "status": "success",
                "message": "STK Push sent. Enter your M-Pesa PIN.",
                "checkout_request_id": invoice_id,
                "customer_message": "Check your phone and enter your M-Pesa PIN to complete payment."
            }
        else:
            error = result.get("detail") or result.get("message") or "STK Push failed"
            logger.error("STK Push failed: %s", result)
            raise HTTPException(status_code=400, detail=str(error))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Payment initiation error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Payment error: {str(e)}")


# ========== ENDPOINT 2: Check Payment Status ==========
@app.get("/api/mpesa/status/{invoice_id}")
async def check_payment_status(invoice_id: str):
    try:
        # First check our local DB — simulate sets it directly
        local = serialize_doc(pending_transactions_col.find_one({"checkout_request_id": invoice_id}))
        if local and local.get("status") == "completed":
            return {"status": "completed", "checkout_request_id": invoice_id}
        if local and local.get("status") == "failed":
            return {"status": "failed", "result_desc": "Payment was not completed.", "checkout_request_id": invoice_id}

        # Otherwise ask Intasend
        result = intasend_check_status(invoice_id)
        logger.info("Intasend status: %s", result)

        state = (result.get("invoice", {}).get("state") or result.get("state") or "").upper()

        if state in ("COMPLETE", "COMPLETED"):
            status = "completed"
        elif state in ("FAILED", "CANCELLED"):
            status = "failed"
        else:
            status = "pending"

        return {
            "status": status,
            "checkout_request_id": invoice_id,
            "result_desc": result.get("invoice", {}).get("narrative") or "Processing..."
        }

    except Exception as e:
        logger.error("Status check error: %s", str(e))
        return {"status": "pending", "checkout_request_id": invoice_id}


# ========== ENDPOINT 3: Intasend Webhook Callback ==========
@app.post("/api/mpesa/callback")
async def intasend_callback(request: Request):
    """
    Intasend calls this URL when a payment is confirmed.
    Set this in your Intasend dashboard under Webhooks.
    """
    try:
        payload = await request.json()
        logger.info("Intasend callback received: %s", payload)

        # Intasend sends: {invoice_id, state, net_amount, account, etc}
        invoice_id = payload.get("invoice_id") or payload.get("id")
        state = str(payload.get("state") or payload.get("invoice", {}).get("state") or "").upper()
        amount = float(payload.get("net_amount") or payload.get("amount") or 0)
        receipt = payload.get("mpesa_reference") or payload.get("receipt") or invoice_id

        if state in ("COMPLETE", "COMPLETED") and invoice_id:
            pending = serialize_doc(pending_transactions_col.find_one({"checkout_request_id": invoice_id}))
            if pending:
                tenant_id = pending.get("tenant_id")
                amt = amount or pending.get("amount", 0)

                user_doc = users_col.find_one({"id": tenant_id})
                tenant_name = user_doc["name"] if user_doc else "Unknown"

                unit_doc = units_col.find_one({"tenant": tenant_name})
                unit_number = unit_doc["unit_number"] if unit_doc else "Unknown"
                new_balance = max(0, (unit_doc.get("balance", 0) - amt)) if unit_doc else 0

                new_txn = {
                    "id": get_next_transaction_id(),
                    "tenant": tenant_name,
                    "unit": unit_number,
                    "amount": amt,
                    "method": "M-Pesa",
                    "status": "Completed",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "ref": receipt,
                }
                transactions_col.insert_one(new_txn)

                if unit_doc:
                    units_col.update_one({"id": unit_doc["id"]}, {"$set": {"balance": new_balance}})

                pending_transactions_col.update_one(
                    {"checkout_request_id": invoice_id},
                    {"$set": {"status": "completed", "receipt": receipt}}
                )

                logger.info("Callback: payment recorded for %s, amount=%s", tenant_name, amt)

        return {"status": "ok"}

    except Exception as e:
        logger.error("Callback error: %s", str(e))
        return {"status": "ok"}  # Always return 200 to Intasend


# ========== ENDPOINT: Simulate Payment (Sandbox only) ==========
@app.post("/api/mpesa/simulate/{invoice_id}")
async def simulate_payment(invoice_id: str):
    try:
        pending = serialize_doc(pending_transactions_col.find_one({"checkout_request_id": invoice_id}))
        if not pending:
            raise HTTPException(status_code=404, detail="Transaction not found")

        amount = pending.get("amount", 0)
        tenant_id = pending.get("tenant_id")
        fake_receipt = "SIM" + "".join([str(random.randint(0, 9)) for _ in range(9)])

        user_doc = users_col.find_one({"id": tenant_id})
        tenant_name = user_doc["name"] if user_doc else "Unknown"

        unit_doc = units_col.find_one({"tenant": tenant_name})
        unit_number = unit_doc["unit_number"] if unit_doc else "Unknown"
        new_balance = max(0, (unit_doc.get("balance", 0) - amount)) if unit_doc else 0

        new_txn = {
            "id": get_next_transaction_id(),
            "tenant": tenant_name,
            "unit": unit_number,
            "amount": amount,
            "method": "M-Pesa",
            "status": "Completed",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ref": fake_receipt,
        }
        transactions_col.insert_one(new_txn)

        if unit_doc:
            units_col.update_one({"id": unit_doc["id"]}, {"$set": {"balance": new_balance}})

        pending_transactions_col.update_one(
            {"checkout_request_id": invoice_id},
            {"$set": {"status": "completed", "receipt": fake_receipt}}
        )

        logger.info("Simulated payment: tenant=%s, amount=%s, receipt=%s", tenant_name, amount, fake_receipt)

        return {
            "status": "completed",
            "receipt": fake_receipt,
            "amount": amount,
            "tenant": tenant_name,
            "unit": unit_number,
            "message": f"Payment of KES {amount:,.0f} recorded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Simulate error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ========== ENDPOINT 4: Get Pending Transactions ==========
@app.get("/api/mpesa/pending")
async def get_pending_transactions(user=Depends(verify_token)):
    if user.get("role") not in ["admin", "accountant"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return serialize_docs(pending_transactions_col.find({}))

# ========== ⬆️ END OF PAYMENT CODE ⬆️ ==========

# ─── Root Endpoint ─────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Savannah Property Management API v1.0", "status": "running"}
