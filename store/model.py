from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils.models import Timestamp
from werkzeug.utils import import_string

from flask_merchants.core import MerchantsError
from flask_merchants.mixins import IntegrationMixin, PaymentMixin

from .database import db


class Integration(db.Model, IntegrationMixin):
    __tablename__ = "merchants_integrations"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Relationship to payments
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        primaryjoin="and_(Integration.slug == foreign(Payment.integration_slug))",
        viewonly=True,
        back_populates="integration",
    )

    def __str__(self):
        # From IntegrationMixin
        return f"{self.slug}"


class Payment(db.Model, PaymentMixin):
    __tablename__ = "merchants_payment"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Relationship to integration
    integration: Mapped[Optional["Integration"]] = relationship(
        "Integration",
        primaryjoin="and_(Integration.slug == foreign(Payment.integration_slug))",
        viewonly=True,
        back_populates="payments",
    )

    def __str__(self):
        # From PaymentMixin
        return f"{self.merchants_token}"

    def process(self):
        if not self.integration:
            raise MerchantsError(f"Integration: {self.integration_slug} does not exist.")

        if not self.integration.is_active:
            raise MerchantsError(f"Integration: {self.integration_slug} is not active.")

        try:
            integration = import_string(self.integration.integration_class)
            return integration.create()
        except MerchantsError as err:
            raise err


class Product(db.Model, Timestamp):
    __tablename__ = "store_product"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    extra_attrs: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    def __str__(self):
        return f"{self.slug}"
