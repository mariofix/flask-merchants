"""Tests for the webhook endpoint."""

import hashlib
import hmac
import json

import pytest
from flask import Flask

from flask_merchants import FlaskMerchants
from flask_merchants.signals import webhook_event_finished, webhook_event_received


def _sign(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature matching the merchants SDK format."""
    mac = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


@pytest.fixture
def webhook_app():
    """App with MERCHANTS_WEBHOOK_SECRET configured."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["MERCHANTS_WEBHOOK_SECRET"] = "test-webhook-secret"
    FlaskMerchants(app)
    return app


@pytest.fixture
def webhook_client(webhook_app):
    return webhook_app.test_client()


# ---------------------------------------------------------------------------
# Without signature verification
# ---------------------------------------------------------------------------


def test_webhook_no_secret(client):
    """Webhook endpoint accepts requests when no secret is configured."""
    payload = json.dumps(
        {
            "payment_id": "dummy_pay_abc",
            "event_type": "payment.succeeded",
            "event_id": "dummy_evt_xyz",
        }
    ).encode()

    resp = client.post(
        "/merchants/webhook",
        data=payload,
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["received"] is True
    assert data["payment_id"] == "dummy_pay_abc"
    assert data["event_type"] == "payment.succeeded"


def test_webhook_updates_store(client, ext):
    """Webhook endpoint updates the stored state for a known payment."""
    # First create a checkout session
    resp = client.post("/merchants/checkout", json={"amount": "1.00", "currency": "USD"})
    session_id = resp.get_json()["transaction_id"]

    payload = json.dumps(
        {
            "payment_id": session_id,
            "event_type": "payment.succeeded",
            "event_id": "evt_001",
        }
    ).encode()

    client.post(
        "/merchants/webhook",
        data=payload,
        content_type="application/json",
    )

    stored = ext.get_session(session_id)
    assert stored["payment_status"] == "succeeded"


def test_webhook_emits_webhook_event_received_signal(client, app):
    """Webhook emits webhook_event_received with parsed event details."""
    captured = []

    def _receiver(sender, **kwargs):
        captured.append((sender, kwargs))

    webhook_event_received.connect(_receiver, sender=app, weak=False)
    try:
        payload = json.dumps(
            {
                "payment_id": "dummy_pay_abc",
                "event_type": "payment.succeeded",
                "event_id": "dummy_evt_xyz",
            }
        ).encode()
        resp = client.post(
            "/merchants/webhook",
            data=payload,
            content_type="application/json",
        )
    finally:
        webhook_event_received.disconnect(_receiver, sender=app)

    assert resp.status_code == 200
    assert len(captured) == 1
    sender, signal_payload = captured[0]
    assert sender is app
    assert signal_payload["event_type"] == "payment.succeeded"
    assert signal_payload["payment_id"] == "dummy_pay_abc"


def test_webhook_emits_webhook_event_finished_signal(client, app):
    """Webhook emits webhook_event_finished after processing."""
    captured = []

    def _receiver(sender, **kwargs):
        captured.append((sender, kwargs))

    webhook_event_finished.connect(_receiver, sender=app, weak=False)
    try:
        payload = json.dumps(
            {
                "payment_id": "dummy_pay_abc",
                "event_type": "payment.succeeded",
                "event_id": "dummy_evt_xyz",
            }
        ).encode()
        resp = client.post(
            "/merchants/webhook",
            data=payload,
            content_type="application/json",
        )
    finally:
        webhook_event_finished.disconnect(_receiver, sender=app)

    assert resp.status_code == 200
    assert len(captured) == 1
    sender, signal_payload = captured[0]
    assert sender is app
    assert signal_payload["event_type"] == "payment.succeeded"
    assert signal_payload["payment_id"] == "dummy_pay_abc"


# ---------------------------------------------------------------------------
# With signature verification
# ---------------------------------------------------------------------------


def test_webhook_valid_signature(webhook_client):
    """Valid HMAC signature is accepted."""
    payload = json.dumps({"payment_id": "pay_1", "event_type": "payment.succeeded"}).encode()
    sig = _sign(payload, "test-webhook-secret")

    resp = webhook_client.post(
        "/merchants/webhook",
        data=payload,
        content_type="application/json",
        headers={"X-Merchants-Signature": sig},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["received"] is True


def test_webhook_invalid_signature(webhook_client):
    """Invalid signature returns 400."""
    payload = json.dumps({"payment_id": "pay_1"}).encode()

    resp = webhook_client.post(
        "/merchants/webhook",
        data=payload,
        content_type="application/json",
        headers={"X-Merchants-Signature": "sha256=badsignature"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "invalid signature" in data["error"]


def test_webhook_missing_signature_with_secret(webhook_client):
    """Missing signature when secret is configured returns 400."""
    payload = json.dumps({"payment_id": "pay_1"}).encode()

    resp = webhook_client.post(
        "/merchants/webhook",
        data=payload,
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_webhook_malformed_payload(client):
    """Non-JSON payload is handled gracefully."""
    resp = client.post(
        "/merchants/webhook",
        data=b"not-json",
        content_type="text/plain",
    )
    # DummyProvider's parse_webhook handles non-JSON by using defaults
    assert resp.status_code in (200, 400)
