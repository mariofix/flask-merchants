"""Blinker signals emitted by flask-merchants."""

from __future__ import annotations

from blinker import Namespace

_signals = Namespace()

merchants_initialized = _signals.signal("merchants-initialized")
checkout_session_saved = _signals.signal("checkout-session-saved")
payment_state_changed = _signals.signal("payment-state-changed")
webhook_event_received = _signals.signal("webhook-event-received")
webhook_event_finished = _signals.signal("webhook-event-finished")
payment_created = _signals.signal("payment-created")
payment_creation_failed = _signals.signal("payment-creation-failed")
payment_started = _signals.signal("payment-started")

__all__ = [
    "checkout_session_saved",
    "merchants_initialized",
    "payment_created",
    "payment_creation_failed",
    "payment_started",
    "payment_state_changed",
    "webhook_event_finished",
    "webhook_event_received",
]
