from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils.models import Timestamp
from werkzeug.utils import import_string

from flask_merchants.core import MerchantsError
from flask_merchants.mixins import IntegrationMixin, PaymentMixin
from flask_security.models import fsqla_v3 as fsqla

from .database import db


class Role(db.Model, fsqla.FsRoleMixin):

    def __str__(self):
        return f"{self.name}"


class User(db.Model, fsqla.FsUserMixin):
    branches: Mapped[list["Branch"]] = relationship(back_populates="partner", cascade="all, delete-orphan")
    settings: Mapped[list["Settings"]] = relationship(back_populates="user")
    students: Mapped[list["Student"]] = relationship(back_populates="user")

    def __str__(self):
        return f"{self.username}"


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


## Tienda


class Category(db.Model, Timestamp):
    __tablename__ = "store_category"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(default=True)

    # Relationship
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    def __str__(self):
        return f"{self.slug}"


class ProductType(db.Model, Timestamp):
    __tablename__ = "store_product_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=False)

    # Relationship
    products: Mapped[list["Product"]] = relationship(back_populates="product_type")

    def __str__(self):
        return f"{self.slug}"


class Branch(db.Model, Timestamp):
    __tablename__ = "store_branch"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    extra_attrs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Foreign Key
    partner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)

    # Relationships
    partner: Mapped["User"] = relationship(back_populates="branches")
    products: Mapped[list["Product"]] = relationship(secondary="store_branch_product", back_populates="branches")

    def __str__(self):
        return f"{self.slug}"


# Association table for Branch-Product many-to-many
class BranchProduct(db.Model):
    __tablename__ = "store_branch_product"

    branch_id: Mapped[int] = mapped_column(ForeignKey("store_branch.id"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("store_product.id"), primary_key=True)
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    active: Mapped[bool] = mapped_column(default=True)


# Update Product model
class Product(db.Model, Timestamp):
    __tablename__ = "store_product"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    extra_attrs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Foreign Keys
    category_id: Mapped[int] = mapped_column(ForeignKey("store_category.id"), nullable=False, index=True)
    product_type_id: Mapped[int] = mapped_column(ForeignKey("store_product_type.id"), nullable=False, index=True)

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="products")
    product_type: Mapped["ProductType"] = relationship(back_populates="products")
    branches: Mapped[list["Branch"]] = relationship(secondary="store_branch_product", back_populates="products")

    def __str__(self):
        return f"{self.name}"


class Settings(db.Model, Timestamp):
    __tablename__ = "store_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[None | int] = mapped_column(ForeignKey("user.id"), nullable=True, default=None)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(default=True)
    value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="settings")

    def __str__(self):
        return f"{self.slug} - {self.user_id}"


class Student(db.Model, Timestamp):
    __tablename__ = "store_student"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[None | int] = mapped_column(ForeignKey("user.id"), nullable=True, default=None)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    daily_limit: Mapped[int] = mapped_column()
    weekly_limit: Mapped[int] = mapped_column()

    user: Mapped["User"] = relationship(back_populates="students")


## Lector


class Operador(db.Model, Timestamp):
    __tablename__ = "reader_operator"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo_qr: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    en_turno: Mapped[bool] = mapped_column(default=True)
    linea: Mapped[int]


class lecturas(db.Model, Timestamp):
    __tablename__ = "reader_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo_qr: Mapped[str]
    linea: Mapped[int]
    camara: Mapped[int]
