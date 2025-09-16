
from sqlalchemy import Column, Integer, Enum, Boolean, JSON, DateTime, Index
from app.database import Base

CouponTypes = ("cart-wise", "product-wise", "bxgy")


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(*CouponTypes, name="coupon_type"), nullable=False, index=True)
    details = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_redemptions = Column(Integer, nullable=True)
    times_redeemed = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_coupons_active_type", "is_active", "type"),
    )
