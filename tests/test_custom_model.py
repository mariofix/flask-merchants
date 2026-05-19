"""Tests for custom model support via PaymentMixin.

Verifies that a developer can bring their own SQLAlchemy model (e.g. Pagos)
and have FlaskMerchants store/retrieve payments through it.
"""

from decimal import Decimal

import pytest
from flask import Flask
from flask_admin import Admin
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from flask_merchants import FlaskMerchants
from flask_merchants.contrib.sqla import PaymentModelView
from flask_merchants.models import PaymentMixin
from flask_merchants.signals import payment_started, payment_status_changed

# ---------------------------------------------------------------------------
# Fixtures: custom Pagos model backed by in-memory SQLite
# ---------------------------------------------------------------------------


@pytest.fixture
def pagos_app():
    """Flask app where FlaskMerchants uses the custom Pagos model."""

    class Base(DeclarativeBase):
        pass

    db = SQLAlchemy(model_class=Base)

    class Pagos(PaymentMixin, db.Model):
        __tablename__ = "pagos"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.config["SECRET_KEY"] = "test-secret"
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    Babel(application)
    db.init_app(application)

    ext = FlaskMerchants(application, db=db, model=Pagos)

    admin_inst = Admin(application, name="Test Admin")
    admin_inst.add_view(PaymentModelView(Pagos, db.session, ext=ext, name="Pagos", endpoint="pagos"))

    application.extensions["test_db"] = db
    application.extensions["test_ext"] = ext
    application.extensions["test_model"] = Pagos

    with application.app_context():
        db.create_all()

    return application


@pytest.fixture
def pagos_client(pagos_app):
    return pagos_app.test_client()


@pytest.fixture
def pagos_db(pagos_app):
    return pagos_app.extensions["test_db"]


@pytest.fixture
def pagos_ext(pagos_app):
    return pagos_app.extensions["test_ext"]


@pytest.fixture
def Pagos(pagos_app):
    return pagos_app.extensions["test_model"]


# ---------------------------------------------------------------------------
# PaymentMixin
# ---------------------------------------------------------------------------


def test_payment_mixin_fields(Pagos):
    """Pagos model inherits all required payment columns from PaymentMixin."""
    cols = {c.key for c in Pagos.__table__.columns}
    for field in (
        "merchants_id",
        "transaction_id",
        "provider",
        "amount",
        "currency",
        "payment_status",
        "request_payload",
        "response_payload",
    ):
        assert field in cols, f"Missing column: {field}"


def test_payment_mixin_to_dict(Pagos):
    """to_dict returns the expected keys including payload fields."""
    p = Pagos(
        merchants_id="s1",
        transaction_id="t1",
        provider="dummy",
        amount="10.00",
        currency="USD",
        payment_status="pending",
    )
    d = p.to_dict()
    assert d["merchants_id"] == "s1"
    assert d["transaction_id"] == "t1"
    assert d["payment_status"] == "pending"
    assert d["currency"] == "USD"
    assert "request_payload" in d
    assert "response_payload" in d


def test_payment_mixin_repr(Pagos):
    """__repr__ uses the subclass name, not 'Payment'."""
    p = Pagos(merchants_id="s2", payment_status="succeeded")
    assert "Pagos" in repr(p)
    assert "s2" in repr(p)


def test_start_payment_success(pagos_app, pagos_db, Pagos):
    """start_payment creates provider checkout and persists mutation + audit payloads."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-start-1",
            transaction_id="pending-start-1",
            provider="dummy",
            amount=Decimal("12.34"),
            currency="USD",
            payment_status="pending",
            email="user@example.com",
        )
        pagos_db.session.add(record)
        pagos_db.session.commit()

        checkout_url = record.start_payment(
            success_url="https://example.test/success",
            cancel_url="https://example.test/cancel",
            extra_args={"reference": "order-42"},
        )

        assert checkout_url
        assert record.transaction_id.startswith("dummy_sess_")
        assert record.payment_status == "pending"
        assert record.request_payload["success_url"] == "https://example.test/success"
        assert record.request_payload["cancel_url"] == "https://example.test/cancel"
        assert record.request_payload["reference"] == "order-42"
        assert record.response_payload["redirect_url"] == checkout_url
        assert record.extra_args["reference"] == "order-42"

        pagos_db.session.expire_all()
        refreshed = pagos_db.session.query(Pagos).filter_by(id=record.id).first()
        assert refreshed.transaction_id == record.transaction_id
        assert refreshed.response_payload["redirect_url"] == checkout_url


def test_start_payment_emits_signal(pagos_app, pagos_db, Pagos):
    """start_payment emits payment_started with the app as sender."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-start-signal",
            transaction_id="pending-start-signal",
            provider="dummy",
            amount=Decimal("10.00"),
            currency="USD",
            payment_status="pending",
        )
        pagos_db.session.add(record)
        pagos_db.session.commit()

        captured = []

        def _receiver(sender, **kwargs):
            captured.append((sender, kwargs))

        payment_started.connect(_receiver, sender=pagos_app, weak=False)
        try:
            redirect_url = record.start_payment(
                success_url="https://example.test/success",
                cancel_url="https://example.test/cancel",
            )
        finally:
            payment_started.disconnect(_receiver, sender=pagos_app)

        assert len(captured) == 1
        sender, payload = captured[0]
        assert sender is pagos_app
        assert payload["payment"] is record
        assert payload["redirect_url"] == redirect_url


def test_refund_emits_payment_status_changed_signal(pagos_app, pagos_db, Pagos):
    """refund() emits payment_status_changed with old/new states."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-refund-signal",
            transaction_id="dummy_refund_signal",
            provider="dummy",
            amount=Decimal("10.00"),
            currency="USD",
            payment_status="pending",
        )
        pagos_db.session.add(record)
        pagos_db.session.commit()

        captured = []

        def _receiver(sender, **kwargs):
            captured.append((sender, kwargs))

        payment_status_changed.connect(_receiver, sender=pagos_app, weak=False)
        try:
            record.refund()
        finally:
            payment_status_changed.disconnect(_receiver, sender=pagos_app)

        assert len(captured) == 1
        sender, payload = captured[0]
        assert sender is pagos_app
        assert payload["payment_id"] == "m-refund-signal"
        assert payload["old_status"] == "pending"
        assert payload["new_status"] == "refunded"


def test_start_payment_requires_persisted_record(pagos_app, Pagos):
    """start_payment rejects transient records that are not in the database yet."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-transient",
            transaction_id="pending-transient",
            provider="dummy",
            amount=Decimal("10.00"),
            currency="USD",
            payment_status="pending",
        )

        with pytest.raises(RuntimeError, match="persisted payment record"):
            record.start_payment(
                success_url="https://example.test/success",
                cancel_url="https://example.test/cancel",
            )


def test_start_payment_requires_pending_state(pagos_app, pagos_db, Pagos):
    """start_payment only allows records that are still pending."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-not-pending",
            transaction_id="pending-not-pending",
            provider="dummy",
            amount=Decimal("10.00"),
            currency="USD",
            payment_status="succeeded",
        )
        pagos_db.session.add(record)
        pagos_db.session.commit()

        with pytest.raises(ValueError, match="payment_status='pending'"):
            record.start_payment(
                success_url="https://example.test/success",
                cancel_url="https://example.test/cancel",
            )


def test_start_payment_requires_required_fields(pagos_app, pagos_db, Pagos):
    """start_payment validates required fields before contacting a provider."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-missing-provider",
            transaction_id="pending-missing-provider",
            provider="",
            amount=Decimal("10.00"),
            currency="USD",
            payment_status="pending",
        )
        pagos_db.session.add(record)
        pagos_db.session.commit()

        with pytest.raises(ValueError, match="missing required field"):
            record.start_payment(
                success_url="https://example.test/success",
                cancel_url="https://example.test/cancel",
            )


def test_start_payment_bubbles_provider_errors(pagos_app, pagos_db, Pagos, pagos_ext, monkeypatch):
    """start_payment propagates provider exceptions to the caller."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-provider-error",
            transaction_id="pending-provider-error",
            provider="dummy",
            amount=Decimal("19.99"),
            currency="USD",
            payment_status="pending",
        )
        pagos_db.session.add(record)
        pagos_db.session.commit()

        class _BrokenPayments:
            @staticmethod
            def create_checkout(**_kwargs):
                raise RuntimeError("provider unavailable")

        class _BrokenClient:
            payments = _BrokenPayments()

        monkeypatch.setattr(pagos_ext, "get_client", lambda _provider: _BrokenClient())

        with pytest.raises(RuntimeError, match="provider unavailable"):
            record.start_payment(
                success_url="https://example.test/success",
                cancel_url="https://example.test/cancel",
            )


def test_start_payment_requires_redirect_url(pagos_app, pagos_db, Pagos, pagos_ext, monkeypatch):
    """start_payment fails when provider does not return a redirect URL."""
    with pagos_app.app_context():
        record = Pagos(
            merchants_id="m-no-redirect",
            transaction_id="pending-no-redirect",
            provider="dummy",
            amount=Decimal("8.00"),
            currency="USD",
            payment_status="pending",
        )
        pagos_db.session.add(record)
        pagos_db.session.commit()

        class _State:
            value = "pending"

        class _Session:
            raw = {"simulated": True}
            redirect_url = None
            session_id = "dummy-no-redirect"
            provider = "dummy"
            amount = Decimal("8.00")
            currency = "USD"
            initial_status = _State()

        class _NoRedirectPayments:
            @staticmethod
            def create_checkout(**_kwargs):
                return _Session()

        class _NoRedirectClient:
            payments = _NoRedirectPayments()

        monkeypatch.setattr(pagos_ext, "get_client", lambda _provider: _NoRedirectClient())

        with pytest.raises(RuntimeError, match="redirect URL"):
            record.start_payment(
                success_url="https://example.test/success",
                cancel_url="https://example.test/cancel",
            )

        assert record.transaction_id == "pending-no-redirect"


# ---------------------------------------------------------------------------
# Store helpers with custom model
# ---------------------------------------------------------------------------


def test_save_session_uses_custom_model(pagos_client, pagos_app, pagos_db, Pagos):
    """Checkout stores a row in the custom Pagos table."""
    with pagos_app.app_context():
        resp = pagos_client.post(
            "/merchants/checkout",
            json={"amount": "25.00", "currency": "EUR"},
        )
        assert resp.status_code == 200
        session_id = resp.get_json()["transaction_id"]

        record = pagos_db.session.query(Pagos).filter_by(transaction_id=session_id).first()
        assert record is not None
        assert record.payment_status == "pending"
        assert record.amount == Decimal("25.00")
        assert record.__class__.__name__ == "Pagos"


def test_get_session_from_custom_model(pagos_client, pagos_app, pagos_ext):
    """get_session retrieves data from the custom model table."""
    with pagos_app.app_context():
        resp = pagos_client.post(
            "/merchants/checkout",
            json={"amount": "5.00", "currency": "USD"},
        )
        session_id = resp.get_json()["transaction_id"]

        stored = pagos_ext.get_session(session_id)
        assert stored is not None
        assert stored["transaction_id"] == session_id
        assert stored["amount"] == "5.00"


def test_update_state_on_custom_model(pagos_client, pagos_app, pagos_db, pagos_ext, Pagos):
    """update_payment_status writes to the custom model row."""
    with pagos_app.app_context():
        resp = pagos_client.post(
            "/merchants/checkout",
            json={"amount": "1.00", "currency": "USD"},
        )
        session_id = resp.get_json()["transaction_id"]

        pagos_ext.update_payment_status(session_id, "succeeded")

        record = pagos_db.session.query(Pagos).filter_by(transaction_id=session_id).first()
        assert record.payment_status == "succeeded"


def test_all_sessions_from_custom_model(pagos_client, pagos_app, pagos_ext):
    """all_sessions returns rows from the custom model table."""
    with pagos_app.app_context():
        pagos_client.post("/merchants/checkout", json={"amount": "1.00", "currency": "USD"})
        sessions = pagos_ext.all_sessions()
        assert len(sessions) >= 1
        assert all("transaction_id" in s for s in sessions)


# ---------------------------------------------------------------------------
# Flask-Admin with custom model
# ---------------------------------------------------------------------------


def test_admin_pagos_list(pagos_client, pagos_app):
    """Admin list page renders for the custom model."""
    with pagos_app.app_context():
        resp = pagos_client.get("/admin/pagos/")
        assert resp.status_code == 200


def test_admin_pagos_refund_action(pagos_client, pagos_app, pagos_db, Pagos):
    """Admin refund action marks a Pagos row as refunded."""
    with pagos_app.app_context():
        resp = pagos_client.post("/merchants/checkout", json={"amount": "1.00", "currency": "USD"})
        session_id = resp.get_json()["transaction_id"]

        record = pagos_db.session.query(Pagos).filter_by(transaction_id=session_id).first()
        pk = str(record.id)

        action_resp = pagos_client.post(
            "/admin/pagos/action/",
            data={"action": "refund", "rowid": pk},
        )
        assert action_resp.status_code in (200, 302)

        pagos_db.session.expire_all()
        refreshed = pagos_db.session.query(Pagos).filter_by(transaction_id=session_id).first()
        assert refreshed.payment_status == "refunded"


def test_admin_pagos_sync_action(pagos_client, pagos_app, pagos_db, Pagos):
    """Admin sync action fetches live state from DummyProvider."""
    with pagos_app.app_context():
        resp = pagos_client.post("/merchants/checkout", json={"amount": "1.00", "currency": "USD"})
        session_id = resp.get_json()["transaction_id"]

        record = pagos_db.session.query(Pagos).filter_by(transaction_id=session_id).first()
        assert record.payment_status == "pending"
        pk = str(record.id)

        action_resp = pagos_client.post(
            "/admin/pagos/action/",
            data={"action": "sync", "rowid": pk},
        )
        assert action_resp.status_code in (200, 302)

        pagos_db.session.expire_all()
        refreshed = pagos_db.session.query(Pagos).filter_by(transaction_id=session_id).first()
        # DummyProvider always returns a terminal state
        assert refreshed.payment_status != "pending"
