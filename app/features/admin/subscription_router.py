"""
Subscription & Payment Router
Handles:
  GET  /subscriptions/plans          - List available plans
  POST /subscriptions/apply-promo    - Validate & preview a promo code
  GET  /subscriptions/active-promos  - Public: list visible promo codes
  POST /subscriptions/create-order   - Create Cashfree payment order (with optional promo)
  POST /subscriptions/verify         - Verify payment after Cashfree redirect
  POST /subscriptions/webhook        - Cashfree payment webhook (server-to-server)
  GET  /subscriptions/status         - Get current subscription status for a clinic
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid
import hmac
import hashlib
import json
import os

from app.core.database import get_db
from app.core.deps import get_current_user
from app.features.auth.models import User
from app.features.admin.models import (
    Subscription, SubscriptionPlan, SubscriptionStatus,
    PromoCode, DiscountType,
)
from app.services.cashfree_service import (
    create_payment_order,
    verify_payment_order,
    get_all_plans,
    PLAN_PRICES,
)

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    plan: str               # "monthly" | "annual"
    promo_code: Optional[str] = None


class ApplyPromoRequest(BaseModel):
    code: str
    plan: str               # "monthly" | "annual"


class VerifyPaymentRequest(BaseModel):
    order_id: str           # Cashfree order ID returned by create-order


class SubscriptionResponse(BaseModel):
    id: str
    clinic_id: str
    plan: str
    status: str
    amount: float
    total_amount: float
    promo_code: Optional[str] = None
    discount_amount: Optional[float] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_active_subscription(clinic_id: str, db: Session) -> Optional[Subscription]:
    """Return active/trial subscription for a clinic, or None."""
    return (
        db.query(Subscription)
        .filter(
            Subscription.clinic_id == clinic_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            Subscription.expires_at > datetime.utcnow(),
        )
        .order_by(Subscription.expires_at.desc())
        .first()
    )


def _activate_subscription(sub: Subscription, cf_payment_id: str, db: Session) -> Subscription:
    """Mark subscription as active after successful payment."""
    now = datetime.utcnow()
    sub.status = SubscriptionStatus.ACTIVE
    sub.cf_payment_id = cf_payment_id
    sub.cf_payment_status = "SUCCESS"
    sub.starts_at = now

    if sub.plan == SubscriptionPlan.MONTHLY:
        sub.expires_at = now + timedelta(days=31)
    else:  # annual
        sub.expires_at = now + timedelta(days=366)

    sub.updated_at = now
    db.commit()
    db.refresh(sub)
    return sub


def _validate_and_apply_promo(
    code: str, plan: str, base_amount: float, db: Session
) -> dict:
    """
    Validate a promo code and calculate final amount.

    Returns:
        {
          "valid": True,
          "final_amount": float,        # Amount to charge (0 if free_trial)
          "discount_amount": float,     # INR discount applied
          "trial_days": int | None,     # For free_trial type
          "message": str,               # User-visible description
          "promo": PromoCode,
        }
    Raises HTTPException 400/404 on invalid code.
    """
    promo = db.query(PromoCode).filter(
        PromoCode.code == code.upper().strip()
    ).first()

    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found.")

    if not promo.is_active:
        raise HTTPException(status_code=400, detail="This promo code is no longer active.")

    if promo.expires_at and datetime.utcnow() > promo.expires_at:
        raise HTTPException(status_code=400, detail="This promo code has expired.")

    if promo.max_uses is not None and promo.used_count >= promo.max_uses:
        raise HTTPException(
            status_code=400,
            detail=f"This promo code has reached its usage limit ({promo.max_uses} uses)."
        )

    # Calculate discount
    trial_days = None
    if promo.discount_type == DiscountType.PERCENT:
        discount = round(base_amount * promo.discount_value / 100, 2)
        final = max(0.0, round(base_amount - discount, 2))
        message = f"{int(promo.discount_value)}% off applied — You save ₹{discount:.0f}!"

    elif promo.discount_type == DiscountType.FIXED:
        discount = min(promo.discount_value, base_amount)
        final = max(0.0, round(base_amount - discount, 2))
        message = f"₹{discount:.0f} off applied!"

    else:  # FREE_TRIAL
        trial_days = int(promo.discount_value)
        discount = base_amount
        final = 0.0
        months = round(trial_days / 30)
        message = f"{months} month{'s' if months > 1 else ''} free trial activated — ₹0 billing!"

    return {
        "valid": True,
        "final_amount": final,
        "discount_amount": discount,
        "trial_days": trial_days,
        "message": message,
        "promo": promo,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    """Return all available subscription plans with pricing."""
    return get_all_plans()


@router.get("/active-promos")
async def get_active_promos(db: Session = Depends(get_db)):
    """
    Public endpoint: return visible, active, non-expired promo codes.
    Frontend shows these below the promo input box.
    """
    now = datetime.utcnow()
    promos = (
        db.query(PromoCode)
        .filter(
            PromoCode.is_active == True,
            PromoCode.is_public == True,
            (PromoCode.expires_at == None) | (PromoCode.expires_at > now),
            (PromoCode.max_uses == None) | (PromoCode.used_count < PromoCode.max_uses),
        )
        .order_by(PromoCode.created_at.asc())
        .all()
    )
    return [
        {
            "code": p.code,
            "description": p.description,
            "discount_type": p.discount_type,
            "discount_value": p.discount_value,
            "max_uses": p.max_uses,
            "used_count": p.used_count,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        }
        for p in promos
    ]


@router.post("/apply-promo")
async def apply_promo_code(
    body: ApplyPromoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate a promo code and preview the discounted amount.
    Does NOT consume the code — only create-order does that.
    """
    if body.plan not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="Plan must be 'monthly' or 'annual'.")

    base_amount = PLAN_PRICES[body.plan]["amount"]
    result = _validate_and_apply_promo(body.code, body.plan, base_amount, db)

    return {
        "valid": True,
        "code": body.code.upper().strip(),
        "original_amount": base_amount,
        "final_amount": result["final_amount"],
        "discount_amount": result["discount_amount"],
        "trial_days": result["trial_days"],
        "message": result["message"],
    }


@router.post("/create-order")
async def create_subscription_order(
    body: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a payment order for a subscription plan.

    If promo_code is provided and results in ₹0 amount, Cashfree is skipped
    and a TRIAL subscription is activated directly in the DB.

    Otherwise returns Cashfree payment_session_id for the frontend checkout modal.
    """
    if body.plan not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="Plan must be 'monthly' or 'annual'.")

    # Check if already has active subscription
    existing = _get_active_subscription(current_user.clinic_id, db)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Active subscription already exists. Expires: {existing.expires_at.date()}",
        )

    base_amount = PLAN_PRICES[body.plan]["amount"]
    final_amount = base_amount
    discount_amount = 0.0
    trial_days = None
    applied_code = None

    # Apply promo code if provided
    if body.promo_code:
        promo_result = _validate_and_apply_promo(
            body.promo_code, body.plan, base_amount, db
        )
        final_amount = promo_result["final_amount"]
        discount_amount = promo_result["discount_amount"]
        trial_days = promo_result["trial_days"]
        applied_code = body.promo_code.upper().strip()

    order_id = f"CS-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.utcnow()

    # ── FREE TRIAL PATH (amount = ₹0, skip Cashfree) ─────────────────────────
    if final_amount == 0:
        days = trial_days or 90  # default 90 days if free_trial without explicit days

        subscription = Subscription(
            id=str(uuid.uuid4()),
            clinic_id=current_user.clinic_id,
            user_id=current_user.id,
            plan=SubscriptionPlan(body.plan),
            status=SubscriptionStatus.TRIAL,
            amount=base_amount,
            gst_amount=0,
            total_amount=0,
            promo_code=applied_code,
            discount_amount=discount_amount,
            cf_order_id=order_id,          # Use our internal order_id as reference
            cf_order_token=None,
            cf_payment_id="FREE_TRIAL",
            cf_payment_status="FREE",
            starts_at=now,
            expires_at=now + timedelta(days=days),
            created_at=now,
            updated_at=now,
        )
        db.add(subscription)

        # Atomically increment promo used_count
        if applied_code:
            promo = db.query(PromoCode).filter(
                PromoCode.code == applied_code
            ).with_for_update().first()
            if promo:
                promo.used_count += 1

        db.commit()

        return {
            "order_id": order_id,
            "is_free": True,
            "status": "trial_activated",
            "message": f"Free trial activated! Expires on {(now + timedelta(days=days)).strftime('%d %b %Y')}",
            "expires_at": (now + timedelta(days=days)).isoformat(),
            "amount": 0,
            "plan": body.plan,
        }

    # ── PAID PATH (create Cashfree order) ─────────────────────────────────────
    try:
        cf_result = create_payment_order(
            order_id=order_id,
            plan=body.plan,
            customer_name=current_user.name,
            customer_phone=current_user.mobile_number,
            customer_email=current_user.email,
            clinic_id=current_user.clinic_id,
            user_id=current_user.id,
            amount_override=final_amount,   # pass discounted amount
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Save pending subscription record
    subscription = Subscription(
        id=str(uuid.uuid4()),
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        plan=SubscriptionPlan(body.plan),
        status=SubscriptionStatus.PENDING,
        amount=base_amount,
        gst_amount=0,
        total_amount=final_amount,
        promo_code=applied_code,
        discount_amount=discount_amount,
        cf_order_id=cf_result["cf_order_id"],
        cf_order_token=cf_result["payment_session_id"],
        created_at=now,
        updated_at=now,
    )
    db.add(subscription)

    # Atomically increment promo used_count (reserve on order creation)
    if applied_code:
        promo = db.query(PromoCode).filter(
            PromoCode.code == applied_code
        ).with_for_update().first()
        if promo:
            promo.used_count += 1

    db.commit()

    return {
        "order_id": order_id,
        "cf_order_id": cf_result["cf_order_id"],
        "payment_session_id": cf_result["payment_session_id"],
        "is_free": False,
        "original_amount": base_amount,
        "amount": final_amount,
        "discount_amount": discount_amount,
        "promo_code": applied_code,
        "plan": body.plan,
        "currency": "INR",
        "environment": os.getenv("CASHFREE_ENV", "TEST"),
    }


@router.post("/verify")
async def verify_subscription_payment(
    body: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verify payment status after Cashfree redirect.
    Called by frontend after user completes payment.
    """
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.cf_order_id == body.order_id,
            Subscription.user_id == current_user.id,
        )
        .first()
    )

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription order not found.")

    # Already active (free trial or previously verified)
    if sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL):
        return {
            "status": "already_active",
            "subscription": SubscriptionResponse.model_validate(sub),
        }

    # Verify with Cashfree
    try:
        cf_status = verify_payment_order(body.order_id)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    payment_status = cf_status.get("payment_status", "PENDING")

    if payment_status == "SUCCESS":
        sub = _activate_subscription(sub, cf_status.get("cf_payment_id", ""), db)
        return {
            "status": "success",
            "message": "Subscription activated successfully!",
            "subscription": SubscriptionResponse.model_validate(sub),
        }
    elif payment_status == "FAILED":
        sub.status = SubscriptionStatus.CANCELLED
        sub.cf_payment_status = "FAILED"
        sub.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=402, detail="Payment failed. Please try again.")
    else:
        return {
            "status": "pending",
            "message": "Payment is still processing. Please wait.",
            "subscription": SubscriptionResponse.model_validate(sub),
        }


@router.post("/webhook")
async def cashfree_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Cashfree server-to-server webhook endpoint.
    Automatically activates subscriptions after confirmed payment.

    Configure this URL in Cashfree dashboard → Settings → Webhook → Payment Webhook URL
    """
    body_bytes = await request.body()

    # Verify Cashfree signature
    cf_signature = request.headers.get("x-webhook-signature")
    cf_timestamp = request.headers.get("x-webhook-timestamp")
    cf_secret = os.getenv("CASHFREE_SECRET_KEY", os.getenv("CASHFREE_SECRET", ""))

    if cf_signature and cf_timestamp and cf_secret:
        message = f"{cf_timestamp}{body_bytes.decode()}"
        computed = hmac.new(
            cf_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed, cf_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        data = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = data.get("type", "")
    payment_data = data.get("data", {})
    order = payment_data.get("order", {})
    payment = payment_data.get("payment", {})

    cf_order_id = order.get("order_id")
    payment_status = payment.get("payment_status")
    cf_payment_id = str(payment.get("cf_payment_id", ""))

    if not cf_order_id:
        return {"status": "ignored", "reason": "No order_id in webhook"}

    sub = db.query(Subscription).filter(Subscription.cf_order_id == cf_order_id).first()
    if not sub:
        return {"status": "ignored", "reason": "Order not found in database"}

    if event_type == "PAYMENT_SUCCESS_WEBHOOK" or payment_status == "SUCCESS":
        if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL):
            _activate_subscription(sub, cf_payment_id, db)

    elif event_type == "PAYMENT_FAILED_WEBHOOK" or payment_status == "FAILED":
        sub.status = SubscriptionStatus.CANCELLED
        sub.cf_payment_status = "FAILED"
        sub.updated_at = datetime.utcnow()
        db.commit()

    return {"status": "ok"}


@router.get("/status")
async def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current subscription status for the logged-in doctor's clinic."""
    active_sub = _get_active_subscription(current_user.clinic_id, db)

    if active_sub:
        return {
            "has_active_subscription": True,
            "subscription": SubscriptionResponse.model_validate(active_sub),
            "days_remaining": (active_sub.expires_at - datetime.utcnow()).days,
        }

    latest = (
        db.query(Subscription)
        .filter(Subscription.clinic_id == current_user.clinic_id)
        .order_by(Subscription.created_at.desc())
        .first()
    )

    return {
        "has_active_subscription": False,
        "last_subscription": SubscriptionResponse.model_validate(latest) if latest else None,
        "available_plans": get_all_plans(),
    }
