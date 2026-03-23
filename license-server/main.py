"""
Extract — License Server
========================
A small FastAPI service that:
  1. Receives Stripe webhooks and generates license keys on successful payment.
  2. Validates and activates keys when the desktop app phones home.
  3. Emails the customer their key + download links.

Deploy to Railway, Render, or any Python host.

Required environment variables:
  STRIPE_SECRET_KEY          sk_live_...
  STRIPE_WEBHOOK_SECRET      whsec_...
  LICENSE_HMAC_SECRET        (any long random string — keep this private)
  SMTP_HOST                  e.g. smtp.gmail.com
  SMTP_PORT                  587
  SMTP_USER                  your@email.com
  SMTP_PASSWORD              your app password
  FROM_EMAIL                 noreply@yourwebsite.com
  DOWNLOAD_URL_MAC           https://yourwebsite.com/downloads/Extract-mac.dmg
  DOWNLOAD_URL_WIN           https://yourwebsite.com/downloads/Extract-win.exe
  MAX_ACTIVATIONS            3  (optional, default 3)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import smtplib
import sqlite3
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import stripe
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Config ───────────────────────────────────────────────────────────────────

STRIPE_SECRET_KEY     = os.environ["STRIPE_SECRET_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]
LICENSE_HMAC_SECRET   = os.environ["LICENSE_HMAC_SECRET"]
SMTP_HOST             = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT             = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER             = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD         = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL            = os.environ.get("FROM_EMAIL", SMTP_USER)
DOWNLOAD_URL_MAC      = os.environ.get("DOWNLOAD_URL_MAC", "https://yourwebsite.com/downloads")
DOWNLOAD_URL_WIN      = os.environ.get("DOWNLOAD_URL_WIN", "https://yourwebsite.com/downloads")
MAX_ACTIVATIONS       = int(os.environ.get("MAX_ACTIVATIONS", "3"))

stripe.api_key = STRIPE_SECRET_KEY

app = FastAPI(title="Extract License Server", docs_url=None, redoc_url=None)

# ── Database ─────────────────────────────────────────────────────────────────

DB_PATH = Path(os.environ.get("DB_PATH", "licenses.db"))


def init_db() -> None:
    with _db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                key              TEXT PRIMARY KEY,
                stripe_session   TEXT UNIQUE NOT NULL,
                customer_email   TEXT NOT NULL,
                created_at       TEXT NOT NULL,
                activations      INTEGER DEFAULT 0,
                machine_ids      TEXT DEFAULT '',
                revoked          INTEGER DEFAULT 0
            )
        """)


@contextmanager
def _db():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


# ── License key generation ────────────────────────────────────────────────────

def _make_key(stripe_session_id: str) -> str:
    """Deterministically generate a license key from a Stripe session ID.

    The key is HMAC-signed so only the server can produce valid keys.
    Format: EXTR-XXXX-XXXX-XXXX-XXXX  (20 uppercase hex chars in 4 groups)
    """
    raw = hmac.new(
        LICENSE_HMAC_SECRET.encode(),
        stripe_session_id.encode(),
        hashlib.sha256,
    ).hexdigest()[:20].upper()
    groups = [raw[i:i+5] for i in range(0, 20, 5)]
    return "EXTR-" + "-".join(groups)


# ── Email ─────────────────────────────────────────────────────────────────────

def _send_license_email(to_email: str, customer_name: str, license_key: str) -> None:
    subject = "Your Extract license key"
    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, Helvetica, sans-serif; color: #111827; max-width: 560px; margin: 0 auto; padding: 32px 16px;">
  <p style="font-size: 11px; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; color: #B08D3C; margin-bottom: 24px;">
    Extract — Technical Analysis Platform
  </p>
  <h1 style="font-size: 24px; font-weight: 700; color: #0B2347; margin-bottom: 8px;">
    Your license key
  </h1>
  <p style="color: #6B7280; margin-bottom: 28px;">
    Hi {customer_name or "there"}, thank you for your purchase.
    Here is your Extract license key:
  </p>

  <div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 10px; padding: 20px 24px; margin-bottom: 28px; text-align: center;">
    <span style="font-family: 'SF Mono', Menlo, monospace; font-size: 22px; font-weight: 700; letter-spacing: 0.08em; color: #0B2347;">
      {license_key}
    </span>
  </div>

  <p style="color: #374151; margin-bottom: 20px;">
    Enter this key in the Extract app when prompted on first launch.
    You can activate on up to {MAX_ACTIVATIONS} machines.
  </p>

  <p style="font-weight: 600; color: #111827; margin-bottom: 8px;">Download Extract:</p>
  <p style="margin-bottom: 6px;">
    <a href="{DOWNLOAD_URL_MAC}" style="color: #1A56DB;">macOS (.dmg)</a>
  </p>
  <p style="margin-bottom: 28px;">
    <a href="{DOWNLOAD_URL_WIN}" style="color: #1A56DB;">Windows (.exe)</a>
  </p>

  <hr style="border: none; border-top: 1px solid #E5E7EB; margin-bottom: 20px;">
  <p style="font-size: 12px; color: #9CA3AF;">
    Keep this email — it contains your license key.
    Questions? Reply to this email.
  </p>
</body>
</html>
"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = FROM_EMAIL
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html"))

    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[license] SMTP not configured — skipping email to {to_email}")
        return

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        print(f"[license] License email sent to {to_email}")
    except Exception as e:
        print(f"[license] Failed to send email to {to_email}: {e}")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """Receive Stripe webhooks. Listens for checkout.session.completed."""
    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id     = session["id"]
        customer_email = session.get("customer_details", {}).get("email") or session.get("customer_email", "")
        customer_name  = session.get("customer_details", {}).get("name", "")

        if not customer_email:
            print(f"[license] No email on session {session_id} — skipping")
            return JSONResponse({"received": True})

        key = _make_key(session_id)
        now = datetime.now(timezone.utc).isoformat()

        with _db() as db:
            existing = db.execute(
                "SELECT key FROM licenses WHERE stripe_session = ?", (session_id,)
            ).fetchone()

            if not existing:
                db.execute(
                    "INSERT INTO licenses (key, stripe_session, customer_email, created_at) VALUES (?, ?, ?, ?)",
                    (key, session_id, customer_email, now),
                )
                print(f"[license] Created key {key} for {customer_email}")
                _send_license_email(customer_email, customer_name, key)
            else:
                print(f"[license] Duplicate webhook for session {session_id} — ignored")

    return JSONResponse({"received": True})


class ActivateRequest(BaseModel):
    license_key: str
    machine_id: str   # opaque fingerprint from the app


class ActivateResponse(BaseModel):
    valid: bool
    message: str


@app.post("/activate", response_model=ActivateResponse)
def activate_license(body: ActivateRequest):
    """Called by the app on first launch to validate and record activation."""
    key = body.license_key.strip().upper()
    mid = body.machine_id.strip()

    if not key or not mid:
        return ActivateResponse(valid=False, message="Invalid request.")

    with _db() as db:
        row = db.execute("SELECT * FROM licenses WHERE key = ?", (key,)).fetchone()

        if not row:
            return ActivateResponse(valid=False, message="License key not found.")

        if row["revoked"]:
            return ActivateResponse(valid=False, message="This license has been revoked.")

        # Parse existing machine IDs
        existing_ids: list[str] = [m for m in row["machine_ids"].split(",") if m]

        if mid in existing_ids:
            # Already activated on this machine — allow
            return ActivateResponse(valid=True, message="Activated.")

        if len(existing_ids) >= MAX_ACTIVATIONS:
            return ActivateResponse(
                valid=False,
                message=(
                    f"This license has reached its activation limit ({MAX_ACTIVATIONS} machines). "
                    "Please contact support to reset."
                ),
            )

        # Register this machine
        existing_ids.append(mid)
        db.execute(
            "UPDATE licenses SET activations = activations + 1, machine_ids = ? WHERE key = ?",
            (",".join(existing_ids), key),
        )

    return ActivateResponse(valid=True, message="Activated.")


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    print(f"[license] Database: {DB_PATH.resolve()}")
