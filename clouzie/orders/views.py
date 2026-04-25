from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from accounts.models import Address
from django.contrib import messages
from cart.models import CartItem
from decimal import Decimal
from .models import Order,OrderItem
import random
from django.utils import timezone
# Create your views here.
@login_required
def create_order(request):
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        address_id = request.POST.get('address_id')
        coupon_code = request.POST.get('coupon_code','').strip()
        
        if not payment_method:
            messages.error(request,"please select payment method")
            return redirect('checkout:checkout')
        
        allowed_methods = ["cod", "razorpay", "wallet"]
        if payment_method not in allowed_methods:
            messages.error(request, "Invalid payment method.")
            return redirect("checkout:checkout")

        if not address_id:
            messages.error(request, "Please select address")
            return redirect('checkout:checkout')
        
        address = get_object_or_404(Address,id=address_id,user=request.user)
        
        
        cart_item = CartItem.objects.filter(cart__user=request.user).select_related('variant','variant__product')
        if not cart_item.exists():
            messages.error(request,"Cart is empty.")
            return redirect('cart')
        
        subtotal = Decimal('0.00')
        delivery_charge = Decimal('0.00')
        discount_amount = Decimal('0.00')
        
        for item in cart_item:
            variant = item.variant
            product = variant.product
            subtotal += variant.price * item.quantity
            if not variant.is_active:
                messages.error(request,f'{variant.product.name} Unavailable.')
                return redirect('cart')
            
            if not product.is_active:
                messages.error(request,f"{product.name} is unavailable.")
                return redirect("cart")
            
            if getattr(variant, "is_deleted", False):
                messages.error(request,f"{product.name} is unavailable.")
                return redirect("cart")
            
            if getattr(product, "is_deleted", False):
                messages.error(request,f"{product.name} is unavailable.")
                return redirect("cart")

            if item.quantity > variant.stock:
                messages.error(request,f'only {variant.stock} items avaiable ')
                return redirect('cart')
            
        if subtotal < 999:
            delivery_charge = Decimal(99.00)
        if coupon_code:
            discount_amount = Decimal('0.00')
        
        total_amount = subtotal - discount_amount + delivery_charge
        
        order_id = f"CLOUZIE-{timezone.now():%y%m%d}-{random.randint(1000,9999)}"
        
        order = Order.objects.create(
            user=request.user,
            address=address,
            coupon_code=coupon_code if coupon_code else None,
            order_id=order_id,
            payment_status="PENDING",
            order_status='CONFIRMED',
            subtotal=subtotal,
            discount_amount=discount_amount,
            delivery_charge=delivery_charge,
            payment_method=payment_method,
            total_amount = total_amount,
        )
        
        for item in cart_item:
            variant = item.variant
            
            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                variant_name=f'{variant.size} + {variant.color}',
                price=variant.price,
                quantity=item.quantity,
                total=variant.price * item.quantity,
                status='CONFIRMED',
            )

            variant.stock -= item.quantity
            variant.save()
            
        cart_item.delete()
        messages.success(request,"Order placed successfully.")
        return redirect('orders:order_success', order_uuid=order.uuid)
    return redirect('checkout:checkout')
@login_required
def order_success(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)
    return render(request,"checkout/order_success.html", {"order": order})