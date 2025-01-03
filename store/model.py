from sqlalchemy.orm import Mapped, mapped_column

from flask_merchants.mixins import IntegrationMixin, PaymentMixin

from .database import db


class Integration(db.Model, IntegrationMixin):
    __tablename__ = "merchants_integrations"

    id: Mapped[int] = mapped_column(primary_key=True)


class Payment(db.Model, PaymentMixin):
    __tablename__ = "merchants_payment"

    id: Mapped[int] = mapped_column(primary_key=True)

    def __str__(self):
        # From PaymentMixin
        return f"{self.merchants_token}"
