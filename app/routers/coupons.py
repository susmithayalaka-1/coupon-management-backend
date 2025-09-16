
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict
from decimal import Decimal
from app.database import get_db
from app.schemas.coupon import (
    CouponCreate, CouponUpdate, CouponResponse, Cart, ApplicableCouponsResponse, ApplicableCoupon,
    ApplyCouponResponse, UpdatedCart, CartItemWithDiscount
)
from app.services.coupon_service import CouponService
from app.services.discount_calculator import DiscountCalculator, D, round2

router = APIRouter(prefix="", tags=["coupons"])


@router.post("/coupons", response_model=CouponResponse, status_code=201)
def create_coupon(coupon: CouponCreate, db: Session = Depends(get_db)):
    created = CouponService.create_coupon(db, coupon)
    return created


@router.get("/coupons", response_model=List[CouponResponse])
def list_coupons(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return CouponService.get_coupons(db, skip, limit)


@router.get("/coupons/{coupon_id}", response_model=CouponResponse)
def get_coupon(coupon_id: int, db: Session = Depends(get_db)):
    c = CouponService.get_coupon(db, coupon_id)
    if not c:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return c


@router.put("/coupons/{coupon_id}", response_model=CouponResponse)
def update_coupon(coupon_id: int, payload: CouponUpdate, db: Session = Depends(get_db)):
    updated = CouponService.update_coupon(db, coupon_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return updated


@router.delete("/coupons/{coupon_id}", status_code=204)
def delete_coupon(coupon_id: int, db: Session = Depends(get_db)):
    ok = CouponService.delete_coupon(db, coupon_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return


@router.post("/applicable-coupons", response_model=ApplicableCouponsResponse)
def get_applicable_coupons(body: Dict = Body(...), db: Session = Depends(get_db)):
    cart_data = body.get("cart", body)
    cart = Cart(**cart_data)

    applicable = []
    for coupon in CouponService.get_active_coupons(db):
        c_resp = CouponResponse.model_validate(coupon)
        if DiscountCalculator.is_coupon_applicable(cart, c_resp):
            disc = DiscountCalculator.calculate_discount(cart, c_resp)
            applicable.append(ApplicableCoupon(coupon_id=coupon.id, type=coupon.type, discount=float(disc)))
    return ApplicableCouponsResponse(applicable_coupons=applicable)


@router.post("/apply-coupon/{coupon_id}", response_model=ApplyCouponResponse)
def apply_coupon(coupon_id: int, cart: Cart, db: Session = Depends(get_db)):
    c = CouponService.get_coupon(db, coupon_id)
    if not c:
        raise HTTPException(status_code=404, detail="Coupon not found")
    CouponService.ensure_redeemable(c)
    c_resp = CouponResponse.model_validate(c)

    # Calculate discounts and construct updated cart
    total_price = DiscountCalculator.calculate_cart_total(cart)
    total_discount = Decimal(0)

    items_map = {it.product_id: it for it in cart.items}
    free_additions: Dict[int, int] = {}

    if c_resp.type == 'cart-wise':
        total_discount = DiscountCalculator.calculate_cart_wise_discount(cart, c_resp.details)
        # distribute proportionally with round-to-sum
        items_with_discount = []
        subtotal = total_price
        running = Decimal(0)
        for idx, item in enumerate(cart.items, start=1):
            proportion = (D(item.quantity) * D(item.price)) / subtotal if subtotal > 0 else Decimal(0)
            # For last item, adjust to ensure sum equals total_discount
            if idx < len(cart.items):
                item_disc = round2(total_discount * proportion)
                running += item_disc
            else:
                item_disc = round2(total_discount - running)
            items_with_discount.append(CartItemWithDiscount(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_discount=float(item_disc)
            ))
    elif c_resp.type == 'product-wise':
        total_discount = DiscountCalculator.calculate_product_wise_discount(cart, c_resp.details)
        target_id = c_resp.details.get('product_id')
        items_with_discount = []
        for item in cart.items:
            item_disc = Decimal(0)
            if item.product_id == target_id:
                product_total = D(item.quantity) * D(item.price)
                if total_discount > product_total:
                    item_disc = product_total
                else:
                    item_disc = total_discount
            items_with_discount.append(CartItemWithDiscount(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_discount=float(round2(item_disc))
            ))
    elif c_resp.type == 'bxgy':
        total_discount, free_items = DiscountCalculator.calculate_bxgy_discount(cart, c_resp.details)
        # Add free quantities (even if not present originally), with price 0 for added items
        for pid, free_qty in free_items.items():
            if pid in items_map:
                items_map[pid].quantity += free_qty
            else:
                free_additions[pid] = free_qty

        items_with_discount = []
        for item in cart.items:
            disc = Decimal(0)
            if item.product_id in free_items:
                disc = D(free_items[item.product_id]) * D(item.price)
            items_with_discount.append(CartItemWithDiscount(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_discount=float(round2(disc))
            ))
        # Include newly added free items at price 0
        for pid, qty in free_additions.items():
            items_with_discount.append(CartItemWithDiscount(
                product_id=pid, quantity=qty, price=0.0, total_discount=0.0
            ))
    else:
        raise HTTPException(status_code=400, detail="Unsupported coupon type")

    final_total_discount = float(round2(total_discount))
    total_price_float = float(round2(total_price))
    final_price = total_price_float - final_total_discount

    # Increment redemption count
    CouponService.increment_redemption(db, c)

    return ApplyCouponResponse(updated_cart=UpdatedCart(
        items=items_with_discount,
        total_price=total_price_float,
        total_discount=final_total_discount,
        final_price=float(round2(Decimal(final_price)))
    ))
