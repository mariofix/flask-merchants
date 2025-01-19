from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
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
