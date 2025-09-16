
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException
from app.models.coupon import Coupon
from app.schemas.coupon import CouponCreate, CouponUpdate


class CouponService:
    """Service class for CRUD operations on coupons"""

    @staticmethod
    def create_coupon(db: Session, coupon_data: CouponCreate) -> Coupon:
        CouponService._validate_coupon_details(coupon_data.type, coupon_data.details)
        db_coupon = Coupon(
            type=coupon_data.type,
            details=coupon_data.details,
            is_active=True if coupon_data.is_active is None else coupon_data.is_active,
            expires_at=coupon_data.expires_at,
            max_redemptions=coupon_data.max_redemptions,
        )
        db.add(db_coupon)
        db.commit()
        db.refresh(db_coupon)
        return db_coupon

    @staticmethod
    def get_coupon(db: Session, coupon_id: int) -> Optional[Coupon]:
        return db.query(Coupon).filter(Coupon.id == coupon_id).first()

    @staticmethod
    def get_coupons(db: Session, skip: int = 0, limit: int = 100) -> List[Coupon]:
        limit = min(max(limit, 1), 500)
        return db.query(Coupon).offset(skip).limit(limit).all()

    @staticmethod
    def get_active_coupons(db: Session) -> List[Coupon]:
        now = datetime.now(timezone.utc)
        q = db.query(Coupon).filter(Coupon.is_active == True)
        # filter out expired
        return [c for c in q.all() if (c.expires_at is None or c.expires_at > now) and (c.max_redemptions is None or c.times_redeemed < c.max_redemptions)]

    @staticmethod
    def update_coupon(db: Session, coupon_id: int, coupon_data: CouponUpdate) -> Optional[Coupon]:
        db_coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not db_coupon:
            return None

        # Compute final fields then validate
        final_type = coupon_data.type if coupon_data.type is not None else db_coupon.type
        final_details = coupon_data.details if coupon_data.details is not None else db_coupon.details
        CouponService._validate_coupon_details(final_type, final_details)

        db_coupon.type = final_type
        db_coupon.details = final_details
        if coupon_data.is_active is not None:
            db_coupon.is_active = coupon_data.is_active
        if coupon_data.expires_at is not None:
            db_coupon.expires_at = coupon_data.expires_at
        if coupon_data.max_redemptions is not None:
            db_coupon.max_redemptions = coupon_data.max_redemptions

        db.commit()
        db.refresh(db_coupon)
        return db_coupon

    @staticmethod
    def delete_coupon(db: Session, coupon_id: int) -> bool:
        db_coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not db_coupon:
            return False
        db.delete(db_coupon)
        db.commit()
        return True

    @staticmethod
    def increment_redemption(db: Session, coupon: Coupon) -> None:
        coupon.times_redeemed += 1
        db.commit()
        db.refresh(coupon)

    @staticmethod
    def _validate_coupon_details(coupon_type: str, details: dict) -> None:
        if coupon_type == 'cart-wise':
            required_fields = ['threshold', 'discount']
            for field in required_fields:
                if field not in details:
                    raise HTTPException(status_code=400, detail=f"Missing required field '{field}' for cart-wise coupon")
                if not isinstance(details[field], (int, float)) or details[field] <= 0:
                    raise HTTPException(status_code=400, detail=f"Field '{field}' must be a positive number")
            if 'discount_type' in details and details['discount_type'] not in ('percentage', 'fixed'):
                raise HTTPException(status_code=400, detail="discount_type must be 'percentage' or 'fixed'")
        elif coupon_type == 'product-wise':
            required_fields = ['product_id', 'discount']
            for field in required_fields:
                if field not in details:
                    raise HTTPException(status_code=400, detail=f"Missing required field '{field}' for product-wise coupon")
            if not isinstance(details['product_id'], int) or details['product_id'] <= 0:
                raise HTTPException(status_code=400, detail="product_id must be a positive integer")
            if not isinstance(details['discount'], (int, float)) or details['discount'] <= 0:
                raise HTTPException(status_code=400, detail="discount must be a positive number")
            if 'discount_type' in details and details['discount_type'] not in ('percentage', 'fixed'):
                raise HTTPException(status_code=400, detail="discount_type must be 'percentage' or 'fixed'")
        elif coupon_type == 'bxgy':
            for key in ['buy_products', 'get_products']:
                if key not in details or not isinstance(details[key], list) or not details[key]:
                    raise HTTPException(status_code=400, detail=f"{key} must be a non-empty list")
            for buy in details['buy_products']:
                if not isinstance(buy, dict) or 'product_id' not in buy or 'quantity' not in buy:
                    raise HTTPException(status_code=400, detail="Each buy_product must have product_id and quantity")
                if not isinstance(buy['product_id'], int) or buy['product_id'] <= 0:
                    raise HTTPException(status_code=400, detail="product_id in buy_products must be a positive integer")
                if not isinstance(buy['quantity'], int) or buy['quantity'] <= 0:
                    raise HTTPException(status_code=400, detail="quantity in buy_products must be a positive integer")
            for get in details['get_products']:
                if not isinstance(get, dict) or 'product_id' not in get or 'quantity' not in get:
                    raise HTTPException(status_code=400, detail="Each get_product must have product_id and quantity")
                if not isinstance(get['product_id'], int) or get['product_id'] <= 0:
                    raise HTTPException(status_code=400, detail="product_id in get_products must be a positive integer")
                if not isinstance(get['quantity'], int) or get['quantity'] <= 0:
                    raise HTTPException(status_code=400, detail="quantity in get_products must be a positive integer")
            if 'repetition_limit' in details:
                if not isinstance(details['repetition_limit'], int) or details['repetition_limit'] <= 0:
                    raise HTTPException(status_code=400, detail="repetition_limit must be a positive integer")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported coupon type: {coupon_type}")

    @staticmethod
    def ensure_redeemable(coupon: Coupon) -> None:
        now = datetime.now(timezone.utc)
        if not coupon.is_active:
            raise HTTPException(status_code=400, detail="Coupon is inactive")
        if coupon.expires_at is not None and coupon.expires_at <= now:
            raise HTTPException(status_code=400, detail="Coupon is expired")
        if coupon.max_redemptions is not None and coupon.times_redeemed >= coupon.max_redemptions:
            raise HTTPException(status_code=400, detail="Coupon redemption limit reached")
