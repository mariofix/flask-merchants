import datetime
import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum, Numeric, String
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
    is_active: Mapped[bool] = True
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
    creation: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_update: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )


# @declarative_mixin
# class PaymentEventMixin:
#     ___abstract__ = True

#     @classmethod
#     def __declare_last__(cls):
#         """
#         From Claude: to add the event before_insert directly on the abstract model

#         """

#         event.listen(cls, "before_insert", cls.event_before_insert)

#     @staticmethod
#     def event_before_insert(mapper, connection, target):
#         if target.status == "created":
#             integration_info = get_integration(slug=target.integration_slug)
#             try:
#                 integration_class = getattr(integrations, integration_info["integration_class"])
#                 integration = integration_class()
#             except Exception as e:
#                 raise e

#             new_payment = integration.create_payment()

#             target.integration_transaction = new_payment.get("token", None)
#             target.status = PaymentStatus.processing
#             target.integration_response = new_payment

#             return target
