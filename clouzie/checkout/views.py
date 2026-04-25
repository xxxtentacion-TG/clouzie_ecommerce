# views.py

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from cart.models import CartItem
from accounts.models import Address
from orders.models import Order,OrderItem


@login_required(login_url="signin")
def checkout_view(request):
    # Get cart items
    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related("variant", "variant__product")

    # Empty cart check
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    # Price calculation
    subtotal = Decimal("0.00")

    for item in cart_items:
        item_total = item.variant.price * item.quantity
        item.item_total = item_total
        subtotal += item_total

    shipping = Decimal("0.00")
    discount = Decimal("0.00")
    grand_total = subtotal - discount + shipping

    addresses = Address.objects.filter(user=request.user,is_default=True)
    

    context = {
        "cart_items": cart_items,
        "addresses": addresses,
        "subtotal": subtotal,
        "shipping": shipping,
        "discount": discount,
        "grand_total": grand_total,
    }

    return render(request, "checkout/checkout.html", context)