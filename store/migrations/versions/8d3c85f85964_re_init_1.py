"""(re)Init-1

Revision ID: 8d3c85f85964
Revises:
Create Date: 2025-01-02 20:37:01.900513

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8d3c85f85964"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "merchants_integrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("integration_class", sa.String(length=255), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchants_integrations")),
        sa.UniqueConstraint("slug", name=op.f("uq_merchants_integrations_slug")),
    )
    op.create_table(
        "merchants_payment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchants_token", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            sa.Enum("created", "processing", "declined", "cancelled", "refunded", "paid", name="paymentstatus"),
            nullable=False,
        ),
        sa.Column("integration_slug", sa.String(length=255), nullable=False),
        sa.Column("integration_transaction", sa.String(length=255), nullable=True),
        sa.Column("integration_payload", sa.JSON(), nullable=True),
        sa.Column("integration_response", sa.JSON(), nullable=True),
        sa.Column(
            "creation", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "last_update", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchants_payment")),
        sa.UniqueConstraint("merchants_token", name=op.f("uq_merchants_payment_merchants_token")),
    )
    with op.batch_alter_table("merchants_payment", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_merchants_payment_integration_slug"), ["integration_slug"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_merchants_payment_integration_transaction"), ["integration_transaction"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_merchants_payment_status"), ["status"], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("merchants_payment", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_merchants_payment_status"))
        batch_op.drop_index(batch_op.f("ix_merchants_payment_integration_transaction"))
        batch_op.drop_index(batch_op.f("ix_merchants_payment_integration_slug"))

    op.drop_table("merchants_payment")
    op.drop_table("merchants_integrations")
    # ### end Alembic commands ###