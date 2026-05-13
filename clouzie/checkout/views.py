# views.py

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from orders.models import Order, OrderItem
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal
from cart.models import CartItem
from accounts.models import Address
from adminpanel.models import Coupon
from utils.offer import get_best_offer


@login_required(login_url="signin")
def checkout_view(request):
    original_total = Decimal("0.00")
    request.session.pop("applied_coupon", None)

    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related("variant", "variant__product")

    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    # ===============================
    # 🛒 SUBTOTAL WITH OFFER
    # ===============================
    subtotal = Decimal("0.00")

    for item in cart_items:
        original_price = item.variant.price

        # 🔥 APPLY OFFER (same as cart)
        original_price = item.variant.price

        final_price, discount_amount, *_ = get_best_offer(
            item.variant.product,
            item.variant.price,
        )
        if final_price is None:
            final_price = original_price
            
        if original_price > final_price:
            offer_percent = int(((original_price - final_price) / original_price) * 100)
        else:
            offer_percent = 0

        item.original_price = original_price
        item.final_price = final_price
        item.offer_percent = offer_percent
        item.item_total = final_price * item.quantity
        item.item_original_total = original_price * item.quantity

        subtotal += item.item_total
        original_total += original_price * item.quantity
    # ===============================
    # 🚚 SHIPPING
    # ===============================
    shipping = Decimal("0.00")
    discount = original_total - subtotal
    # ===============================
    # 🎟 COUPON
    # ===============================
    applied_coupon = request.session.get("applied_coupon")
    coupon_discount = Decimal("0.00")

    if applied_coupon and applied_coupon.get("code"):
        coupon_discount = Decimal(str(applied_coupon.get("discount", 0)))

    # ===============================
    # 💰 FINAL TOTAL
    # ===============================
    grand_total = subtotal - coupon_discount + shipping

    if grand_total < 0:
        grand_total = Decimal("0.00")

    # ===============================
    # 📍 ADDRESS
    # ===============================
    all_addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-id')
    default_address = all_addresses.filter(is_default=True).first() or all_addresses.first()

    # ===============================
    # 🎟 AVAILABLE COUPONS
    # ===============================
    available_coupons = Coupon.objects.filter(
        is_deleted=False,
        is_active=True
    )

    # ===============================
    # 📦 CONTEXT
    # ===============================
    context = {
        "cart_items": cart_items,
        "addresses": [default_address] if default_address else [],
        "all_addresses": all_addresses,
        "selected_address": default_address,
        "subtotal": subtotal,
        "shipping": shipping,
        "coupon_discount": coupon_discount,
        "grand_total": grand_total,
        "discount":discount,
        "available_coupons": available_coupons,
    }

    return render(request, "checkout/checkout.html", context)

import json

@require_POST
def apply_coupon(request):
    
    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip().upper()

        if not code:
            return JsonResponse({"error": "Coupon code is required."}, status=400)

        # 🔍 Get coupon
        try:
            coupon = Coupon.objects.get(
                code=code,
                is_active=True,
                is_deleted=False
            )
        except Coupon.DoesNotExist:
            return JsonResponse({"error": "Invalid coupon."}, status=400)

        used_count = Order.objects.filter(
        user=request.user,
        coupon_code=coupon.code
    ).exclude(order_status="CANCELLED").count()

        if coupon.usage_limit_per_user and used_count >= coupon.usage_limit_per_user:
            return JsonResponse({
                "error": "You have already used this coupon maximum times"
                }, status=400)
        today = timezone.now().date()

        # ⛔ Expiry check
        if coupon.start_date > today or coupon.end_date < today:
            return JsonResponse({"error": "Coupon expired or not started."}, status=400)

        # 🛒 Get cart items
        cart_items = CartItem.objects.filter(
            cart__user=request.user
        ).select_related('variant')

        if not cart_items.exists():
            return JsonResponse({"error": "Cart is empty."}, status=400)

        # 💰 Calculate subtotal
        subtotal = Decimal("0.00")

        for item in cart_items:

            final_price, best_discount, best_percentage = get_best_offer(
                product=item.variant.product,
                base_price=item.variant.price,
            )

            subtotal += final_price * item.quantity

        # 🚫 Min purchase check
        if subtotal < coupon.min_purchase:
            return JsonResponse({
                "error": f"Minimum purchase ₹{coupon.min_purchase} required."
            }, status=400)

        # 💸 Calculate discount
        if coupon.discount_type == "PERCENTAGE":
            discount = (subtotal * coupon.discount_value) / Decimal("100")

            # Apply max cap
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)

        else:  # FIXED
            discount = coupon.discount_value

        # 🧮 Final total
        new_total = subtotal - discount
        if new_total < 0:
            new_total = Decimal("0.00")

        # 💾 Store in session (important)
        request.session["applied_coupon"] = {
            "code": coupon.code,
            "discount": str(discount)
        }

        return JsonResponse({
            "success": True,
            "coupon": coupon.code,
            "discount": float(discount),
            "new_total": float(new_total)
        })

    except Exception as e:
        return JsonResponse({
            "error": "Something went wrong.",
            "debug": str(e)  # remove in production
        }, status=500)
        
        
def remove_coupon(request):
    request.session.pop("applied_coupon", None)
    return JsonResponse({"success": True})
        
        