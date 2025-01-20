import datetime
import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, Numeric, String
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column
from sqlalchemy.sql import func

from .core import PaymentStatus


@declarative_mixin
class IntegrationMixin:
    """
    A mixin class for handling integrations-related attributes and functionality.

    This abstract class provides common fields and methods for integration support.
    """

    ___abstract__ = True

    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    integration_class: Mapped[str] = mapped_column(String(255), nullable=True)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)


@declarative_mixin
class PaymentMixin:
    """
    A mixin class for handling payment-related attributes and functionality.

    This abstract class provides common fields and methods for payment processing,
    including account information, transaction details, and payment status.
    """

    ___abstract__ = True
    merchants_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=False, unique=True, default=uuid.uuid4
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.created, index=True)
    integration_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    integration_transaction: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    integration_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    integration_response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    creation: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        insert_default=func.now(),
    )
    last_update: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        server_onupdate=func.now(),
        server_default=func.now(),
        insert_default=func.now(),
    )
