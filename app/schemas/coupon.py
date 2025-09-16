from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


# Base schemas for different coupon types
class CartWiseDetails(BaseModel):
    threshold: float = Field(..., gt=0, description="Minimum cart value required")
    discount: float = Field(..., gt=0, description="Discount percentage or fixed amount")
    discount_type: str = Field(default="percentage", description="'percentage' or 'fixed'")


class ProductWiseDetails(BaseModel):
    product_id: int = Field(..., gt=0)
    discount: float = Field(..., gt=0)
    discount_type: str = Field(default="percentage", description="'percentage' or 'fixed'")


class BuyProduct(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class GetProduct(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class BxGyDetails(BaseModel):
    buy_products: List[BuyProduct]
    get_products: List[GetProduct]
    repetition_limit: int = Field(default=1, gt=0)


# Union type for coupon details
CouponDetails = Union[CartWiseDetails, ProductWiseDetails, BxGyDetails]


# Request schemas
class CouponCreate(BaseModel):
    type: str = Field(..., description="Type of coupon: 'cart-wise', 'product-wise', 'bxgy'")
    details: Dict[str, Any] = Field(..., description="Coupon-specific configuration")
    is_active: Optional[bool] = Field(default=True)
    expires_at: Optional[datetime] = None
    max_redemptions: Optional[int] = Field(default=None, ge=1)


class CouponUpdate(BaseModel):
    type: Optional[str] = Field(None, description="Type of coupon")
    details: Optional[Dict[str, Any]] = Field(None, description="Coupon-specific configuration")
    is_active: Optional[bool] = Field(None, description="Whether coupon is active")
    expires_at: Optional[datetime] = None
    max_redemptions: Optional[int] = Field(default=None, ge=1)


# Response schemas
class CouponResponse(BaseModel):
    id: int
    type: str
    details: Dict[str, Any]
    is_active: bool
    expires_at: Optional[datetime] = None
    max_redemptions: Optional[int] = None
    times_redeemed: int

    # Pydantic v2 style config (replaces class Config)
    model_config = ConfigDict(from_attributes=True)


# Cart related schemas
class CartItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0, description="Price per unit")


class Cart(BaseModel):
    items: List[CartItem]


# Response schemas for coupon application
class ApplicableCoupon(BaseModel):
    coupon_id: int
    type: str
    discount: float


class ApplicableCouponsResponse(BaseModel):
    applicable_coupons: List[ApplicableCoupon]


class CartItemWithDiscount(BaseModel):
    product_id: int
    quantity: int
    price: float
    total_discount: float = Field(default=0.0)


class UpdatedCart(BaseModel):
    items: List[CartItemWithDiscount]
    total_price: float
    total_discount: float
    final_price: float


class ApplyCouponResponse(BaseModel):
    updated_cart: UpdatedCart
