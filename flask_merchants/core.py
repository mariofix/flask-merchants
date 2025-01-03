import enum


class PaymentStatus(enum.Enum):
    created = "created"
    processing = "processing"
    declined = "declined"
    cancelled = "cancelled"
    refunded = "refunded"
    paid = "paid"
