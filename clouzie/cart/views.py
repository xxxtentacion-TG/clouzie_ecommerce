from django.shortcuts import render, get_object_or_404, redirect
from adminpanel.models import Products, Subcategory, Category, Variants
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from cart.models import Cart, CartItem
from accounts.models import CustomUser
from django.db.models import Sum, F
from utils.offer import get_best_offer
from django.contrib.auth.decorators import login_required

def get_cart_totals(user):
    cart = Cart.objects.get(user=user)
    cart_items = CartItem.objects.filter(cart=cart)

    sub_total = 0
    original_total = 0
    
    for item in cart_items:
        final_price, best_discount, best_percentage = get_best_offer(
            product=item.variant.product,
            base_price=item.variant.price,
        )
        sub_total += final_price * item.quantity
        original_total += item.variant.price * item.quantity

    delivery_charge = 0
    grand_total = sub_total + delivery_charge
    saved_amount = original_total - sub_total

    return {
        "sub_total": sub_total,
        "original_total": original_total,
        "delivery_charge": delivery_charge,
        "grand_total": grand_total,
        "saved_amount": saved_amount,
        "cart_count": cart_items.count(),
    }

@login_required
def cart(request):
    user_id = request.user.id
    user_obj = get_object_or_404(CustomUser, id=user_id)
    cart = Cart.objects.get(user=user_obj)
    cart_items = CartItem.objects.filter(cart=cart).order_by('-variant_id')

    sub_total = 0
    original_total = 0  
    variant_total = 0
    checkout_blocked = False

    for item in cart_items:
        original_price = item.variant.price

        final_price, best_discount, offer_percentage = get_best_offer(
            product=item.variant.product,
            base_price=item.variant.price,
        )

        if final_price is None:
            final_price = original_price

        if original_price > final_price:
            offer_percent = int(((original_price - final_price) / original_price) * 100)
        else:
            offer_percent = 0

        item.final_price = final_price
        item.item_total = final_price * item.quantity
        item.offer_percent = offer_percent
        item.original_price = original_price 
        item.item_original_total = original_price * item.quantity
        
        sub_total += final_price * item.quantity
        original_total += original_price * item.quantity   

        if item.variant.stock == 0:
            checkout_blocked = True
        if item.quantity > item.variant.stock:
            checkout_blocked = True
        if not item.variant.is_active:
            checkout_blocked = True
        if item.variant.is_deleted:
            checkout_blocked = True
        if not item.variant.product.is_active:
            checkout_blocked = True

    
    delivery_charge = 0
    grand_total = sub_total + delivery_charge

    saved_amount = original_total - sub_total  
    print(saved_amount)
    return render(request, "cart/cart.html", {
        "cart_items": cart_items,
        "sub_total": sub_total,
        "delivery_charge": delivery_charge,
        "grand_total": grand_total,
        "checkout_blocked": checkout_blocked,
        "saved_amount": saved_amount,
        'orginal_total':original_total,
        'variant_total':variant_total,
    })
    
@login_required
def increase(request, id):
    item = get_object_or_404(CartItem, id=id, cart__user=request.user)

    if item.quantity >= item.variant.stock:
        return JsonResponse({
            "success": False,
            "stock": item.variant.stock,
            "message": f"Only {item.variant.stock} items available in stock"
        })

    if item.quantity >= 5:
        return JsonResponse({
            "success": False,
            "message": "Maximum 5 items allowed per product"
        })

    item.quantity += 1
    item.save()

    final_price, best_discount, best_percentage = get_best_offer(
        product=item.variant.product,
        base_price=item.variant.price,
    )

    totals = get_cart_totals(request.user)
    return JsonResponse({
        "success": True,
        "quantity": item.quantity,
        "stock": item.variant.stock,
        "item_total": float(final_price * item.quantity),
        "item_original_total": float(item.variant.price * item.quantity),
        "sub_total": float(totals["sub_total"]),
        "original_total": float(totals["original_total"]),
        "delivery_charge": float(totals["delivery_charge"]),
        "grand_total": float(totals["grand_total"]),
        "saved_amount": float(totals["saved_amount"]),
        "cart_count": totals["cart_count"],
    })

@login_required
def decrease(request, id):
    item = get_object_or_404(CartItem, id=id, cart__user=request.user)

    if item.quantity > 1:
        item.quantity -= 1
        item.save()

        final_price, best_discount, best_percentage = get_best_offer(
            product=item.variant.product,
            base_price=item.variant.price,
        )

        totals = get_cart_totals(request.user)

        return JsonResponse({
            "success": True,
            "quantity": item.quantity,
            "stock": item.variant.stock,
            "item_total": float(final_price * item.quantity),
            "item_original_total": float(item.variant.price * item.quantity),
            "sub_total": float(totals["sub_total"]),
            "original_total": float(totals["original_total"]),
            "delivery_charge": float(totals["delivery_charge"]),
            "grand_total": float(totals["grand_total"]),
            "saved_amount": float(totals["saved_amount"]),
            "cart_count": totals["cart_count"],
        })

    return JsonResponse({
        "success": False,
        "message": "Quantity cannot be less than 1"
    })

@login_required
def remove_item(request, id):
    item = get_object_or_404(CartItem, id=id, cart__user=request.user)
    item.delete()

    totals = get_cart_totals(request.user)

    return JsonResponse({
        "success": True,
        "sub_total": float(totals["sub_total"]),
        "original_total": float(totals["original_total"]),
        "delivery_charge": float(totals["delivery_charge"]),
        "grand_total": float(totals["grand_total"]),
        "saved_amount": float(totals["saved_amount"]),
        "cart_count": totals["cart_count"],
    })
