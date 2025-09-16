
from typing import Dict, Tuple
from decimal import Decimal, ROUND_HALF_UP, getcontext
from app.schemas.coupon import Cart, CouponResponse

getcontext().prec = 28


def D(x) -> Decimal:
    return Decimal(str(x))


def round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class DiscountCalculator:
    """Service class to calculate discounts for different coupon types"""

    @staticmethod
    def calculate_cart_total(cart: Cart) -> Decimal:
        return sum(D(item.quantity) * D(item.price) for item in cart.items)

    @staticmethod
    def calculate_cart_wise_discount(cart: Cart, coupon_details: dict) -> Decimal:
        cart_total = DiscountCalculator.calculate_cart_total(cart)
        threshold = D(coupon_details.get('threshold', 0))
        discount = D(coupon_details.get('discount', 0))
        discount_type = coupon_details.get('discount_type', 'percentage')

        if cart_total < threshold:
            return D(0)
        if discount_type == 'percentage':
            return round2((cart_total * discount) / D(100))
        else:
            return min(round2(discount), cart_total)

    @staticmethod
    def calculate_product_wise_discount(cart: Cart, coupon_details: dict) -> Decimal:
        product_id = coupon_details.get('product_id')
        discount = D(coupon_details.get('discount', 0))
        discount_type = coupon_details.get('discount_type', 'percentage')

        target_item = next((it for it in cart.items if it.product_id == product_id), None)
        if not target_item:
            return D(0)

        product_total = D(target_item.quantity) * D(target_item.price)
        if discount_type == 'percentage':
            return round2((product_total * discount) / D(100))
        else:
            return min(round2(discount), product_total)

    @staticmethod
    def calculate_bxgy_discount(cart: Cart, coupon_details: dict) -> Tuple[Decimal, Dict[int, int]]:
        buy_products = coupon_details.get('buy_products', [])
        get_products = coupon_details.get('get_products', [])
        repetition_limit = coupon_details.get('repetition_limit', 1)

        cart_items = {item.product_id: item for item in cart.items}

        total_buy_quantity = 0
        required_buy_quantity = 0
        for buy_product in buy_products:
            product_id = buy_product.get('product_id')
            required_quantity = buy_product.get('quantity')
            required_buy_quantity += required_quantity
            if product_id in cart_items:
                total_buy_quantity += cart_items[product_id].quantity

        if required_buy_quantity == 0:
            return D(0), {}

        times_applicable = min(total_buy_quantity // required_buy_quantity, repetition_limit)

        free_items: Dict[int, int] = {}
        total_discount = D(0)

        for get_product in get_products:
            product_id = get_product.get('product_id')
            free_quantity_per_application = get_product.get('quantity')

            total_free_quantity = free_quantity_per_application * times_applicable

            # If the GET product is in cart, discount those; if not, we still grant free items by adding them
            if product_id in cart_items:
                item_price = D(cart_items[product_id].price)
            else:
                # If not in cart, assume a price of 0 for discount purposes (cannot compute without catalog).
                # We will add the free items with price as provided when applying coupon (router will set price=0 for added free items).
                item_price = D(0)

            if total_free_quantity > 0:
                free_items[product_id] = total_free_quantity
                total_discount += D(total_free_quantity) * item_price

        return round2(total_discount), free_items

    @staticmethod
    def is_coupon_applicable(cart: Cart, coupon: CouponResponse) -> bool:
        # Basic active/expiry checks are handled at service layer; here we check logical applicability
        if coupon.type == 'cart-wise':
            cart_total = DiscountCalculator.calculate_cart_total(cart)
            threshold = D(coupon.details.get('threshold', 0))
            return cart_total >= threshold
        elif coupon.type == 'product-wise':
            product_id = coupon.details.get('product_id')
            return any(item.product_id == product_id for item in cart.items)
        elif coupon.type == 'bxgy':
            buy_products = coupon.details.get('buy_products', [])
            cart_items = {item.product_id: item for item in cart.items}
            total_buy_quantity = 0
            required_buy_quantity = 0
            for buy_product in buy_products:
                product_id = buy_product.get('product_id')
                required_quantity = buy_product.get('quantity')
                required_buy_quantity += required_quantity
                if product_id in cart_items:
                    total_buy_quantity += cart_items[product_id].quantity
            return required_buy_quantity > 0 and total_buy_quantity >= required_buy_quantity
        return False

    @staticmethod
    def calculate_discount(cart: Cart, coupon: CouponResponse) -> Decimal:
        if not DiscountCalculator.is_coupon_applicable(cart, coupon):
            return D(0)
        if coupon.type == 'cart-wise':
            return DiscountCalculator.calculate_cart_wise_discount(cart, coupon.details)
        elif coupon.type == 'product-wise':
            return DiscountCalculator.calculate_product_wise_discount(cart, coupon.details)
        elif coupon.type == 'bxgy':
            discount, _ = DiscountCalculator.calculate_bxgy_discount(cart, coupon.details)
            return discount
        return D(0)
