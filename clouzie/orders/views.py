from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from accounts.models import Address
from django.contrib import messages
from cart.models import CartItem
from decimal import Decimal, ROUND_HALF_UP
from .models import Order, OrderItem, ReturnRequest
import random
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json
import razorpay
from django.conf import settings
from adminpanel.models import Coupon, Variants
from django.db import transaction
from wallet.models import Wallet
from utils.offer import get_best_offer
from reviews.models import Review



RETURN_WINDOW_DAYS = 7
EXCLUDED_STATUSES  = frozenset({'CANCELLED', 'RETURNED'})


# ═══════════════════════════════════════════════════════════════════════════════
# REFUND MATH — single source of truth
# ───────────────────────────────────────────────────────────────────────────────
# item.price          = unit price AFTER product offer, BEFORE coupon
# item.total          = item.price × quantity  (pre-coupon)
# order.subtotal      = sum(item.total) for all items at creation (pre-coupon)
# order.discount_amount = coupon discount saved at order creation
# order.total_amount  = subtotal - discount + tax + delivery
#
# Refund for one cancelled item:
#   item_value          = item.price × item.quantity
#   pre_cancel_subtotal = sum of ALL active item values BEFORE this cancel
#   coupon_share        = (item_value / pre_cancel_subtotal) × original_coupon
#   refund              = item_value - coupon_share   (min 0)
#
# CRITICAL: always snapshot order.discount_amount BEFORE calling
# update_order_status() — that function zeros discount_amount when all items
# are cancelled, which would corrupt the refund calculation.
# ═══════════════════════════════════════════════════════════════════════════════

from decimal import Decimal, ROUND_HALF_UP

def calculate_refund(item, order):
    item_value      = item.price * item.quantity
    base_subtotal   = order.original_subtotal or order.subtotal
    # Always use the original coupon — never the mutated discount_amount
    original_coupon = order.coupon_discount or Decimal("0.00")

    if base_subtotal > 0 and original_coupon > 0:
        coupon_share = (item_value / base_subtotal) * original_coupon
    else:
        coupon_share = Decimal("0.00")

    refund = item_value - coupon_share
    return max(refund, Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ───────────────────────────────────────────────────────────────────────────────

def update_order_status(order):
    items = list(order.items.all())
    if not items:
        return

    statuses = [item.status for item in items]

    if all(s == 'CANCELLED' for s in statuses):
        order.order_status = 'CANCELLED'
    elif all(s in ['RETURNED', 'CANCELLED'] for s in statuses):
        order.order_status = 'RETURNED'
    elif any(s in ['RETURN_REQUESTED', 'RETURNED'] for s in statuses):
        order.order_status = 'PARTIALLY_RETURNED'
    elif any(s == 'CANCELLED' for s in statuses):
        order.order_status = 'PARTIALLY_CANCELLED'

    active_items  = [i for i in items if i.status not in ['CANCELLED', 'RETURNED']]
    new_subtotal  = sum(i.total for i in active_items)

    # Use the immutable original values as the base — never the mutated running values
    original_subtotal = order.original_subtotal or order.subtotal
    original_coupon   = order.coupon_discount or Decimal("0.00")

    if original_subtotal > 0 and original_coupon > 0:
        discount_ratio        = original_coupon / original_subtotal
        order.discount_amount = (new_subtotal * discount_ratio).quantize(Decimal("0.01"))
    else:
        order.discount_amount = Decimal("0.00")

    order.total_amount = max(
        new_subtotal + order.tax_amount + order.delivery_charge - order.discount_amount,
        Decimal("0.00")
    )
    order.save()


# ───────────────────────────────────────────────────────────────────────────────

def create_order(request):
    if request.method != 'POST':
        return redirect('checkout:checkout')

    payment_method = request.POST.get('payment_method', '').upper()
    address_id     = request.POST.get('address_id')

    if not payment_method:
        messages.error(request, "Please select payment method")
        return redirect('checkout:checkout')

    if payment_method not in ("COD", "RAZORPAY", "WALLET"):
        messages.error(request, "Invalid payment method")
        return redirect('checkout:checkout')

    if not address_id:
        messages.error(request, "Please select address")
        return redirect('checkout:checkout')

    address    = get_object_or_404(Address, id=address_id, user=request.user)
    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        messages.error(request, "Cart is empty")
        return redirect('cart')

    subtotal        = Decimal("0.00")
    delivery_charge = Decimal("0.00")

    for item in cart_items:
        variant = item.variant
        product = variant.product

        final_price, _, _ = get_best_offer(product=product, base_price=variant.price)
        if final_price is None:
            final_price = variant.price

        subtotal        += final_price * item.quantity
        item.final_price = final_price
        item.item_total  = final_price * item.quantity

        if not variant.is_active or not product.is_active:
            messages.error(request, f"{product.name} unavailable")
            return redirect("cart")
        if getattr(variant, "is_deleted", False) or getattr(product, "is_deleted", False):
            messages.error(request, f"{product.name} unavailable")
            return redirect("cart")
        if item.quantity > variant.stock:
            messages.error(request, f"Only {variant.stock} items available")
            return redirect("cart")

    coupon_code     = None
    discount_amount = Decimal("0.00")
    applied_coupon  = request.session.get("applied_coupon")

    if applied_coupon:
        coupon = Coupon.objects.filter(
            code=applied_coupon.get("code"), is_active=True, is_deleted=False
        ).first()
        if coupon:
            today = timezone.now().date()
            if coupon.start_date <= today <= coupon.end_date and subtotal >= coupon.min_purchase:
                coupon_code = coupon.code
                if coupon.discount_type == "PERCENTAGE":
                    discount_amount = (subtotal * coupon.discount_value) / Decimal("100")
                    if coupon.max_discount:
                        discount_amount = min(discount_amount, coupon.max_discount)
                else:
                    discount_amount = coupon.discount_value

    total_amount = subtotal - discount_amount + delivery_charge
    if payment_method == "COD" and total_amount > 1000:
        messages.error(request, "Cash on Delivery is not available for orders above ₹1000.")
        return redirect("checkout:checkout")
    if total_amount < 0:
        total_amount = Decimal("0.00")

    order_id = f"CLOUZIE-{timezone.now():%y%m%d}-{random.randint(1000,9999)}"
    order = Order.objects.create(
        user=request.user, address=address, coupon_code=coupon_code,
        order_id=order_id, payment_status="PENDING", order_status="PENDING",
        subtotal=subtotal, discount_amount=discount_amount,
        coupon_discount=discount_amount,   # immutable original — never mutated
        delivery_charge=delivery_charge, payment_method=payment_method,
        original_subtotal=subtotal,
        total_amount=total_amount,
    )

    for item in cart_items:
        variant             = item.variant
        original_price      = variant.price
        final_price         = item.final_price
        line_offer_discount = (original_price - final_price) * item.quantity
        OrderItem.objects.create(
            order=order, variant=variant,
            product_name=variant.product.name,
            variant_name=f"{variant.size} + {variant.color}",
            original_price=original_price, price=final_price,
            offer_discount=line_offer_discount,
            quantity=item.quantity, total=item.item_total, status="PENDING",
        )

    if payment_method == "WALLET":
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        if wallet.balance < total_amount:
            messages.error(request, "Insufficient wallet balance")
            order.delete()
            return redirect('checkout:checkout')
        with transaction.atomic():
            wallet.debit(total_amount, description="Order payment", order=order)
            order.payment_status = "PAID"
            order.order_status   = "CONFIRMED"
            order.save()
            for item in cart_items:
                item.variant.stock -= item.quantity
                item.variant.save()
            cart_items.delete()
            request.session.pop("applied_coupon", None)
        messages.success(request, "Order placed using wallet")
        return redirect('orders:order_success', order_uuid=order.uuid)

    elif payment_method == "COD":
        order.payment_status = "PENDING"
        order.order_status   = "PENDING"
        order.save()
        for item in cart_items:
            item.variant.stock -= item.quantity
            item.variant.save()
        cart_items.delete()
        request.session.pop("applied_coupon", None)
        messages.success(request, "Order placed successfully")
        return redirect('orders:order_success', order_uuid=order.uuid)

    elif payment_method == "RAZORPAY":
        return redirect("checkout:create_razorpay_order")

    return redirect('checkout:checkout')


@login_required
def create_razorpay_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data       = json.loads(request.body)
    address_id = data.get("address_id")
    if not address_id:
        return JsonResponse({"error": "Please select address"}, status=400)

    address    = get_object_or_404(Address, id=address_id, user=request.user)
    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    subtotal        = Decimal("0.00")
    delivery_charge = Decimal("0.00")
    line_items      = []

    for item in cart_items:
        variant = item.variant
        product = variant.product
        if not variant.is_active or not product.is_active:
            return JsonResponse({"error": f"{product.name} is unavailable"}, status=400)
        if getattr(variant, "is_deleted", False) or getattr(product, "is_deleted", False):
            return JsonResponse({"error": f"{product.name} is unavailable"}, status=400)
        if item.quantity > variant.stock:
            return JsonResponse({"error": f"Only {variant.stock} left for {product.name}"}, status=400)

        final_price, _, _ = get_best_offer(product=product, base_price=variant.price)
        final_price        = final_price or variant.price
        item_total         = final_price * item.quantity
        subtotal          += item_total

        line_items.append({
            "variant_id":     variant.id,
            "product_name":   product.name,
            "variant_name":   f"{variant.size} + {variant.color}",
            "original_price": str(variant.price),
            "final_price":    str(final_price),
            "offer_discount": str((variant.price - final_price) * item.quantity),
            "quantity":       item.quantity,
            "total":          str(item_total),
        })

    coupon_code     = None
    discount_amount = Decimal("0.00")
    applied_coupon  = request.session.get("applied_coupon")

    if applied_coupon:
        coupon = Coupon.objects.filter(
            code=applied_coupon.get("code"), is_active=True, is_deleted=False
        ).first()
        if coupon:
            today = timezone.now().date()
            if coupon.start_date <= today <= coupon.end_date and subtotal >= coupon.min_purchase:
                coupon_code = coupon.code
                if coupon.discount_type == "PERCENTAGE":
                    discount_amount = (subtotal * coupon.discount_value) / Decimal("100")
                    if coupon.max_discount:
                        discount_amount = min(discount_amount, coupon.max_discount)
                else:
                    discount_amount = coupon.discount_value

    total_amount = max(subtotal - discount_amount + delivery_charge, Decimal("0.00"))

    request.session["pending_razorpay_order"] = {
        "address_id":      address_id,
        "subtotal":        str(subtotal),
        "discount_amount": str(discount_amount),
        "delivery_charge": str(delivery_charge),
        "total_amount":    str(total_amount),
        "coupon_code":     coupon_code,
        "line_items":      line_items,
    }

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order = client.order.create({
        "amount": int(total_amount * 100), "currency": "INR", "payment_capture": "1"
    })

    return JsonResponse({
        "key":               settings.RAZORPAY_KEY_ID,
        "amount":            razorpay_order["amount"],
        "razorpay_order_id": razorpay_order["id"],
    })


@login_required
def verify_razorpay_payment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    razorpay_payment_id = data.get("razorpay_payment_id", "").strip()
    razorpay_order_id   = data.get("razorpay_order_id",   "").strip()
    razorpay_signature  = data.get("razorpay_signature",  "").strip()

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return JsonResponse({"error": "Missing payment fields"}, status=400)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id":   razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature":  razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"error": "Payment verification failed. Please contact support."}, status=400)

    pending = request.session.get("pending_razorpay_order")
    if not pending:
        return JsonResponse({"error": "Session expired. Please try again."}, status=400)

    with transaction.atomic():
        address  = get_object_or_404(Address, id=pending["address_id"], user=request.user)
        order_id = f"CLOUZIE-{timezone.now():%y%m%d}-{random.randint(1000,9999)}"
        order    = Order.objects.create(
            user=request.user, address=address,
            coupon_code=pending["coupon_code"], order_id=order_id,
            payment_method="RAZORPAY", payment_status="PAID", order_status="CONFIRMED",
            subtotal=Decimal(pending["subtotal"]),
            discount_amount=Decimal(pending["discount_amount"]),
            coupon_discount=Decimal(pending["discount_amount"]),  # immutable original — never mutated
            original_subtotal=Decimal(pending["subtotal"]),        # immutable original — never mutated
            delivery_charge=Decimal(pending["delivery_charge"]),
            total_amount=Decimal(pending["total_amount"]),
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
        )
        for line in pending["line_items"]:
            variant = Variants.objects.select_for_update().get(id=line["variant_id"])
            OrderItem.objects.create(
                order=order, variant=variant,
                product_name=line["product_name"], variant_name=line["variant_name"],
                original_price=Decimal(line["original_price"]),
                price=Decimal(line["final_price"]),
                offer_discount=Decimal(line["offer_discount"]),
                quantity=line["quantity"], total=Decimal(line["total"]), status="PENDING",
            )
            variant.stock -= line["quantity"]
            variant.save(update_fields=["stock"])

        CartItem.objects.filter(cart__user=request.user).delete()
        request.session.pop("applied_coupon", None)
        request.session.pop("pending_razorpay_order", None)

    return JsonResponse({"success": True, "redirect": f"/orders/order-success/{order.uuid}/"})


@login_required
def order_success(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)
    if order.payment_method == "RAZORPAY" and order.payment_status == "PENDING":
        messages.error(request, "Payment not yet verified. Please complete your payment.")
        return redirect("checkout:checkout")
    return render(request, "checkout/order_success.html", {
        "order": order, "payment_id": order.razorpay_payment_id,
    })


@login_required
def payment_failed(request):
    return render(request, "checkout/order_failed.html", {
        "payment_id": request.GET.get("payment_id")
    })


@login_required
def order_management(request):
    search_query  = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').upper()
    sort_by       = request.GET.get('sort', 'latest')

    orders_list = Order.objects.filter(user=request.user)

    if search_query:
        orders_list = orders_list.filter(
            models.Q(order_id__icontains=search_query) |
            models.Q(items__product_name__icontains=search_query)
        ).distinct()

    if status_filter in ('PENDING', 'CONFIRMED', 'PACKED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED'):
        orders_list = orders_list.filter(order_status=status_filter)

    if sort_by == 'oldest':
        orders_list = orders_list.order_by('placed_at')
    elif sort_by == 'price_high':
        orders_list = orders_list.order_by('-total_amount')
    else:
        orders_list = orders_list.order_by('-placed_at')

    paginator = Paginator(orders_list, 10)
    orders    = paginator.get_page(request.GET.get('page'))

    return render(request, "orders/order_management.html", {
        "orders": orders, "search_query": search_query,
        "status_filter": status_filter, "sort_by": sort_by,
    })


@login_required
def order_details(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    order_level_return = order.return_requests.filter(order_item__isnull=True).first()
    has_return = (
        order_level_return is not None
        or order.order_status in ('RETURN_REQUESTED', 'RETURNED')
    )

    return_eligible          = False
    return_ineligible_reason = ''

    if order.order_status == 'DELIVERED' and not has_return:
        delivered_at = order.delivered_date or order.updated_at
        if timezone.now() <= delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
            return_eligible = True
        else:
            return_ineligible_reason = f'Return window has expired ({RETURN_WINDOW_DAYS} days from delivery).'

    has_full_order_return = ReturnRequest.objects.filter(
        order=order, order_item__isnull=True,
        status__in=['PENDING', 'APPROVED', 'RECEIVED']
    ).exists()

    item_return_eligible_ids = []
    delivered_at = order.delivered_date or order.updated_at
    if delivered_at and timezone.now() <= delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
        item_return_eligible_ids = [
            item.id for item in order.items.all()
            if item.status == 'DELIVERED' and not item.return_request.exists()
        ]

    rr_by_item  = {}
    for rr in order.return_requests.order_by('-requested_at'):
        if rr.order_item_id not in rr_by_item:
            rr_by_item[rr.order_item_id] = rr

    order_items = list(order.items.select_related('variant').all())
    for item in order_items:
        item.current_return = rr_by_item.get(item.id)

    return_steps = []
    if order_level_return:
        step_order  = ['PENDING', 'APPROVED', 'RECEIVED', 'REFUNDED']
        step_labels = ['Requested', 'Approved', 'Collected', 'Refunded']
        s           = order_level_return.status
        current_idx = step_order.index(s) if s in step_order else -1
        return_steps = [(label, idx <= current_idx) for idx, label in enumerate(step_labels)]

    # Items already reviewed by this user for this order
    reviewed_item_ids = set(
        Review.objects.filter(
            user=request.user,
            order_item__in=order.items.all()
        ).values_list('order_item_id', flat=True)
    )

    return render(request, 'orders/order_details.html', {
        'order':                       order,
        'order_items':                 order_items,
        'return_eligible':             return_eligible,
        'return_ineligible_reason':    return_ineligible_reason,
        'has_return':                  has_return,
        'return_request':              order_level_return,
        'return_steps':                return_steps,
        'has_partially_cancelled_items': order.order_status == 'PARTIALLY_CANCELLED',
        'item_return_eligible_ids':    item_return_eligible_ids,
        'has_full_order_return':       has_full_order_return,
        'reviewed_item_ids':           reviewed_item_ids,
    })


# ─── Cancel single item ───────────────────────────────────────────────────────

from django.db import transaction

@login_required
def cancel_order_item(request, item_id):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request'})

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order

    if item.status in ['CANCELLED', 'DELIVERED', 'SHIPPED', 'RETURN_REQUESTED', 'RETURNED']:
        return JsonResponse({'success': False, 'error': 'Item cannot be cancelled'})

    data = json.loads(request.body)
    reason = data.get('reason', '')

    with transaction.atomic():
        refund_amount = calculate_refund(item, order)

        item.status = 'CANCELLED'
        item.cancel_reason = reason
        item.save()

        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

        update_order_status(order)

        if order.payment_method != "COD" and order.payment_status in ["PAID", "SUCCESS"]:
            if refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.credit(
                    refund_amount,
                    description=f"Refund for cancelled item in order {order.order_id}",
                    order=order
                )

    # Refresh order from DB — update_order_status() already saved updated values
    order.refresh_from_db()

    active_items  = order.items.exclude(status__in=['CANCELLED', 'RETURNED'])
    new_subtotal  = sum(i.total for i in active_items)
    all_cancelled = not active_items.exists()

    # For fully-cancelled orders show original total (not 0) for user clarity
    if all_cancelled:
        original      = order.original_subtotal or order.subtotal or Decimal("0.00")
        coupon        = order.coupon_discount    or Decimal("0.00")
        delivery      = order.delivery_charge    or Decimal("0.00")
        display_total = max(original - coupon + delivery, Decimal("0.00"))
    else:
        display_total = order.total_amount

    return JsonResponse({
        "success":       True,
        "message":       "Item cancelled successfully",
        "new_total":     str(display_total),
        "new_subtotal":  str(new_subtotal),
        "new_coupon":    str(order.coupon_discount or "0.00"),
        "new_discount":  str(order.discount_amount  or "0.00"),
        "new_tax":       str(order.tax_amount        or "0.00"),
        "all_cancelled": all_cancelled,
        "refund_amount": str(refund_amount),
        "refund_note": (
            f"₹{refund_amount} has been credited to your wallet."
            if order.payment_method != 'COD' and refund_amount > 0
            else "No refund applicable for COD orders."
        ),
    })


@login_required
def cancel_order(request, order_uuid):
    if request.method != 'POST':
        return redirect('orders:order_details', order_uuid=order_uuid)

    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    CANCELLABLE = ('PENDING', 'CONFIRMED', 'PACKED', 'PARTIALLY_CANCELLED')
    if order.order_status not in CANCELLABLE:
        messages.error(request, "This order cannot be cancelled at its current stage.")
        return redirect('orders:order_details', order_uuid=order_uuid)

    # ── SNAPSHOT before mutation ──────────────────────────────────────────────
    original_coupon = order.discount_amount or Decimal("0.00")
    original_total  = order.total_amount    or Decimal("0.00")

    for item in order.items.select_related('variant').exclude(status__in=EXCLUDED_STATUSES):
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

    if (order.payment_method != 'COD'
            and order.payment_status in ('PAID', 'SUCCESS')
            and order.payment_status != 'REFUNDED'):

        if order.order_status == 'PARTIALLY_CANCELLED':
            # Some items already refunded — refund only remaining active items
            active_items    = order.items.exclude(status__in=EXCLUDED_STATUSES)
            active_subtotal = sum(
                i.price * i.quantity for i in active_items
            ) or Decimal("0.00")
            refund_amount = sum(
    calculate_refund(item, order)
    for item in order.items.exclude(status__in=EXCLUDED_STATUSES)
)
            refund_amount += (order.tax_amount      or Decimal("0.00"))
            refund_amount += (order.delivery_charge or Decimal("0.00"))
        else:
            # Clean full cancel — total_amount is exactly what was paid
            refund_amount = original_total

        refund_amount = max(refund_amount, Decimal("0.00"))
        if refund_amount > 0:
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.credit(
                refund_amount,
                description=f"Refund for cancelled order {order.order_id}",
                order=order,
            )
        order.payment_status = 'REFUNDED'

    order.order_status = 'CANCELLED'
    order.items.exclude(status__in=EXCLUDED_STATUSES).update(status='CANCELLED')
    order.save()

    messages.success(request, "Order cancelled successfully.")
    return redirect('orders:order_details', order_uuid=order_uuid)


# ─── Return item (user-side request) ─────────────────────────────────────────

@login_required
def return_order_item(request, item_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed."})

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    NON_RETURNABLE = (
        'PENDING', 'CONFIRMED', 'PACKED', 'SHIPPED',
        'CANCELLED', 'RETURN_REQUESTED', 'RETURNED',
    )
    if item.status in NON_RETURNABLE:
        return JsonResponse({
            "success": False,
            "error": f"Item cannot be returned (current status: {item.status.replace('_', ' ').title()})."
        })
    if item.status != 'DELIVERED':
        return JsonResponse({"success": False, "error": "Only delivered items can be returned."})
    if item.return_request.exists():
        return JsonResponse({"success": False, "error": "A return request already exists for this item."})

    delivered_at = item.order.delivered_date or item.order.updated_at
    if delivered_at and timezone.now() > delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
        return JsonResponse({"success": False, "error": "Return window has expired."})

    reason = request.POST.get('reason', '').strip()
    notes  = request.POST.get('notes', '').strip()
    image  = request.FILES.get('image')

    if not reason:
        return JsonResponse({"success": False, "error": "Please select a reason."})

    ReturnRequest.objects.create(
        order=item.order, order_item=item, user=request.user,
        reason=reason, notes=notes, image=image,
    )
    item.status = 'RETURN_REQUESTED'
    item.save()

    # No financial recalculation at RETURN_REQUESTED — item still belongs to order.
    # Only update the order status label so the UI reflects the pending return.
    order = item.order
    all_statuses = list(order.items.values_list('status', flat=True))
    if any(s in ('RETURN_REQUESTED', 'RETURNED') for s in all_statuses):
        new_label = 'PARTIALLY_RETURNED'
        if all(s in ('RETURN_REQUESTED', 'RETURNED', 'CANCELLED') for s in all_statuses):
            new_label = 'RETURNED'
        order.order_status = new_label
        order.save(update_fields=['order_status'])

    return JsonResponse({"success": True, "message": "Return requested successfully."})


# ─── Cancel return request (user-side) ───────────────────────────────────────

@login_required
def cancel_return(request, pk):
    rr         = get_object_or_404(ReturnRequest, pk=pk, order__user=request.user)
    order_uuid = rr.order.uuid

    if rr.status == 'PENDING':
        order_item = rr.order_item
        rr.delete()
        if order_item:
            order_item.status = 'DELIVERED'
            order_item.save(update_fields=['status'])
            update_order_status(order_item.order)

    return redirect('orders:order_details', order_uuid=order_uuid)


# ─── Whole-order return request (user-side) ───────────────────────────────────

@login_required
def request_return(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    if order.order_status != 'DELIVERED':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('orders:order_details', order_uuid=order_uuid)
    if order.return_requests.filter(order_item__isnull=True).exists():
        messages.error(request, 'A return request already exists for this order.')
        return redirect('orders:order_details', order_uuid=order_uuid)

    delivered_at = order.delivered_date or order.updated_at
    if timezone.now() > delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
        messages.error(request, 'The return window has expired.')
        return redirect('orders:order_details', order_uuid=order_uuid)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        notes  = request.POST.get('notes',  '').strip()
        image  = request.FILES.get('image')

        if not reason:
            messages.error(request, 'Please select a reason for return.')
            return redirect('orders:order_details', order_uuid=order_uuid)

        ReturnRequest.objects.create(
            order=order, user=request.user,
            reason=reason, notes=notes, image=image,
        )
        order.order_status = 'RETURN_REQUESTED'
        order.save()
        messages.success(request, 'Return request submitted successfully.')
        return redirect('orders:order_details', order_uuid=order_uuid)

    return redirect('orders:order_details', order_uuid=order_uuid)


@login_required
def download_invoice(request, order_uuid):
    import io, os
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from django.http import HttpResponse

    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    if order.order_status in ('CANCELLED', 'RETURNED'):
        messages.error(request, "Invoice is not available for this order.")
        return redirect('orders:order_details', order_uuid=order_uuid)

    items = list(
    order.items.select_related('variant', 'variant__product')
               .prefetch_related('variant__images')
               .exclude(status__in=['CANCELLED', 'RETURNED', 'PARTIALLY_RETURNED', 'PARTIALLY_CANCELLED'])
)
    if not items:
        messages.error(request, "No active items to generate invoice for.")
        return redirect('orders:order_details', order_uuid=order_uuid)

    # Recalculate totals from active items only
    from decimal import Decimal

    invoice_subtotal   = sum(item.total for item in items)
    original_subtotal  = order.original_subtotal or order.subtotal or Decimal("1.00")
    original_coupon    = order.coupon_discount or Decimal("0.00")

    # Proportional coupon discount for active items only
    if original_subtotal > 0 and original_coupon > 0:
        invoice_discount = (invoice_subtotal / original_subtotal) * original_coupon
        invoice_discount = invoice_discount.quantize(Decimal("0.01"))
    else:
        invoice_discount = Decimal("0.00")

    invoice_total = max(
        invoice_subtotal - invoice_discount + (order.tax_amount or Decimal("0.00")) + (order.delivery_charge or Decimal("0.00")),
        Decimal("0.00")
    )
    
    buffer  = io.BytesIO()
    PAGE_W, PAGE_H = A4
    ML = MR = MT = MB = 22 * mm
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)

    BLACK  = colors.HexColor('#0a0a0a')
    DGRAY  = colors.HexColor('#555555')
    MGRAY  = colors.HexColor('#999999')
    LGRAY  = colors.HexColor('#dddddd')
    XLIGHT = colors.HexColor('#f8f8f8')
    WHITE  = colors.white
    W      = PAGE_W - ML - MR

    def S(name, size=9, bold=False, color=BLACK, align=TA_LEFT, lead=None, space=0):
        return ParagraphStyle(
            name, fontName='Helvetica-Bold' if bold else 'Helvetica',
            fontSize=size, textColor=color, alignment=align,
            leading=lead or size * 1.5, spaceBefore=space,
        )
    def P(text, style): return Paragraph(text, style)
    def hr(thick=0.4, color=LGRAY, before=0, after=4):
        return HRFlowable(width='100%', thickness=thick, color=color, spaceBefore=before, spaceAfter=after)
    def rs(v):
        try: return f'Rs. {float(v):.2f}'
        except: return str(v)

    story = []
    story.append(hr(1.8, BLACK, before=0, after=0))
    story.append(Spacer(1, 3 * mm))

    brand_row = Table([[
        P('CLOUZIE', S('brand', 18, True, BLACK)),
        P('INVOICE', S('inv', 18, True, BLACK, TA_RIGHT)),
    ]], colWidths=[W * 0.5, W * 0.5])
    brand_row.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0),(-1,-1), 0), ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('TOPPADDING', (0,0),(-1,-1), 0),  ('BOTTOMPADDING', (0,0),(-1,-1), 0),
    ]))
    story.append(brand_row)
    story.append(Spacer(1, 3 * mm))
    story.append(hr(1.8, BLACK, before=0, after=6))

    placed     = order.placed_at.strftime('%d %b %Y')
    meta_lines = (
        f'Invoice No: INV-{order.order_id}<br/>'
        f'Date: {placed}<br/>'
        f'Payment: {order.get_payment_method_display()} - {order.payment_status.title()}'
    )
    meta_row = Table([[
        P('Premium Fashion | India', S('tag', 7.5, color=MGRAY)),
        P(meta_lines, S('meta', 7.5, color=DGRAY, align=TA_RIGHT, lead=12)),
    ]], colWidths=[W * 0.45, W * 0.55])
    meta_row.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0),(-1,-1), 0), ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('TOPPADDING', (0,0),(-1,-1), 0),  ('BOTTOMPADDING', (0,0),(-1,-1), 0),
    ]))
    story.append(meta_row)
    story.append(Spacer(1, 8 * mm))
    story.append(hr(0.4, LGRAY, after=6))

    addr = order.address
    if addr:
        al2  = (f'{addr.address_line2}<br/>' if getattr(addr, 'address_line2', '') else '')
        bill = (
            f'<b>{addr.full_name}</b><br/>{addr.address_line1}<br/>' + al2 +
            f'{addr.city}, {addr.state} - {addr.pincode}<br/>India<br/>Ph: {addr.phone_number}'
        )
    else:
        bill = 'No address on record.'

    frm = (
        '<b>CLOUZIE</b><br/>123 Fashion Street<br/>'
        'Mumbai, Maharashtra - 400001<br/>India<br/>support@clouzie.com'
    )
    addr_tbl = Table([[
        [P('BILL TO', S('albl', 6.5, True, MGRAY)), Spacer(1, 2), P(bill, S('av', 8, color=BLACK, lead=13))],
        [P('FROM',    S('albl2', 6.5, True, MGRAY)), Spacer(1, 2), P(frm, S('av2', 8, color=BLACK, lead=13))],
    ]], colWidths=[W * 0.48, W * 0.52])
    addr_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0),(-1,-1), 0), ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('LEFTPADDING', (1,0),(1,-1), 6*mm), ('LINEAFTER', (0,0),(0,-1), 0.4, LGRAY),
    ]))
    story.append(addr_tbl)
    story.append(Spacer(1, 8 * mm))
    story.append(hr(0.4, LGRAY, after=4))

    IMG_W = 9 * mm; IMG_H = 12 * mm; ROW_H = IMG_H + 4 * mm
    col_w    = [IMG_W + 2*mm, None, 28*mm, 12*mm, 22*mm, 22*mm]
    col_w[1] = W - sum(c for c in col_w if c)

    ths  = S('th', 7, True, WHITE)
    hrow = [
        P('', ths), P('ITEM', ths), P('SIZE / VAR', ths),
        P('QTY',   S('thc', 7, True, WHITE, TA_CENTER)),
        P('PRICE', S('thr', 7, True, WHITE, TA_RIGHT)),
        P('TOTAL', S('thr2', 7, True, WHITE, TA_RIGHT)),
    ]
    table_rows  = [hrow]
    row_heights = [8*mm]

    for item in items:
        img_cell = P('', S('e', 7))
        has_img  = False
        try:
            if item.variant and item.variant.images.first():
                ipath = item.variant.images.first().image.path
                if os.path.exists(ipath):
                    img_cell = RLImage(ipath, width=IMG_W, height=IMG_H)
                    has_img  = True
        except Exception:
            pass
        table_rows.append([
            img_cell,
            P(item.product_name or '', S('td', 8)),
            P(str(item.variant_name or 'N/A'), S('tdg', 7.5, color=DGRAY)),
            P(str(item.quantity), S('tdc', 8, align=TA_CENTER)),
            P(rs(item.price),     S('tdr', 8, align=TA_RIGHT)),
            P(rs(item.total),     S('tdr2', 8, align=TA_RIGHT)),
        ])
        row_heights.append(ROW_H if has_img else 9*mm)

    items_t = Table(table_rows, colWidths=col_w, rowHeights=row_heights, repeatRows=1)
    items_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0),  BLACK),
        ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,0),  7),
        ('TOPPADDING',    (0,0),(-1,0),  8), ('BOTTOMPADDING', (0,0),(-1,0), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 5), ('RIGHTPADDING',  (0,0),(-1,-1), 5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, XLIGHT]),
        ('FONTNAME',      (0,1),(-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1),(-1,-1), 8),
        ('TOPPADDING',    (0,1),(-1,-1), 4), ('BOTTOMPADDING', (0,1),(-1,-1), 4),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('ALIGN',         (3,1),(3,-1),  'CENTER'),
        ('ALIGN',         (4,1),(-1,-1), 'RIGHT'),
        ('LINEBELOW',     (0,0),(-1,-1), 0.25, LGRAY),
        ('BOX',           (0,0),(-1,-1), 0.4,  LGRAY),
    ]))
    story.append(items_t)
    story.append(Spacer(1, 8 * mm))

    sw       = 68 * mm
    sum_rows = [['SUBTOTAL', rs(invoice_subtotal)]]
    if invoice_discount > 0:
        sum_rows.append(['DISCOUNT', '- ' + rs(invoice_discount)])
    if order.coupon_code:
        sum_rows.append(['COUPON', str(order.coupon_code)])
    sum_rows.append(['SHIPPING', 'Free' if not order.delivery_charge or order.delivery_charge == 0 else rs(order.delivery_charge)])
    sum_rows.append(['TAX', rs(order.tax_amount)])

    inner = [
        [P(r[0], S(f'sl{i}', 7.5, color=MGRAY)), P(r[1], S(f'sr{i}', 7.5, color=BLACK, align=TA_RIGHT))]
        for i, r in enumerate(sum_rows)
    ] + [[
        P('GRAND TOTAL', S('gl', 9, True, BLACK)),
        P(rs(invoice_total), S('gr', 9, True, BLACK, TA_RIGHT)),
    ]]
    inner_t = Table(inner, colWidths=[sw * 0.5, sw * 0.5])
    inner_t.setStyle(TableStyle([
        ('TOPPADDING', (0,0),(-1,-1), 4), ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 0), ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('LINEABOVE',   (0,-1),(-1,-1), 1, BLACK),
        ('TOPPADDING',  (0,-1),(-1,-1), 7), ('BOTTOMPADDING', (0,-1),(-1,-1), 7),
    ]))
    outer_t = Table([['', inner_t]], colWidths=[W - sw, sw])
    outer_t.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0),(-1,-1), 0), ('RIGHTPADDING', (0,0),(-1,-1), 0),
    ]))
    story.append(outer_t)
    story.append(Spacer(1, 10 * mm))
    story.append(hr(0.4, LGRAY, after=5))

    ft = Table([[
        P('Thank you for shopping with CLOUZIE.', S('ft', 7.5, color=DGRAY)),
        P('Questions?  support@clouzie.com  |  +91 98765 43210', S('ft2', 7.5, color=MGRAY, align=TA_RIGHT)),
    ]], colWidths=[W * 0.5, W * 0.5])
    ft.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0),(-1,-1), 0), ('RIGHTPADDING', (0,0),(-1,-1), 0),
    ]))
    story.append(ft)
    story.append(Spacer(1, 3 * mm))
    story.append(hr(1.8, BLACK, before=0, after=0))

    doc.build(story)
    buffer.seek(0)

    resp = HttpResponse(buffer, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="invoice-CLOUZIE-{order.order_id}.pdf"'
    return resp