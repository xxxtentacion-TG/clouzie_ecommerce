from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from accounts.models import Address
from django.contrib import messages
from cart.models import CartItem
from decimal import Decimal
from .models import Order, OrderItem, ReturnRequest
import random
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json
import razorpay
from django.conf import settings
import json, random, razorpay
from adminpanel.models import Coupon
from django.db import transaction
from wallet.models import Wallet

RETURN_WINDOW_DAYS = 7

def update_order_status(order):
    items = list(order.items.all())
    if not items:
        return

    all_statuses = [item.status for item in items]

    all_cancelled  = all(s == 'CANCELLED' for s in all_statuses)
    all_returned   = (
        all(s in ['RETURNED', 'CANCELLED'] for s in all_statuses)
        and any(s == 'RETURNED' for s in all_statuses)
    )
    any_returned   = any(s in ['RETURN_REQUESTED', 'RETURNED'] for s in all_statuses)
    any_cancelled  = any(s == 'CANCELLED' for s in all_statuses)

    if all_cancelled:
        order.order_status = 'CANCELLED'
    elif all_returned:
        order.order_status = 'RETURNED'
    elif any_returned:
        order.order_status = 'PARTIALLY_RETURNED'
    elif any_cancelled:
        order.order_status = 'PARTIALLY_CANCELLED'

    active_items = [i for i in items if i.status not in ['CANCELLED', 'RETURNED']]
    new_subtotal = sum(i.total for i in active_items)
    order.subtotal = new_subtotal

    if all_cancelled or all_returned:
        order.delivery_charge = Decimal('0.00')
        order.tax_amount      = Decimal('0.00')
        order.discount_amount = Decimal('0.00')
        order.total_amount    = Decimal('0.00')
    else:
        if order.discount_amount > new_subtotal:
            order.discount_amount = new_subtotal
        order.total_amount = (
            new_subtotal
            + order.tax_amount
            + order.delivery_charge
            - order.discount_amount
        )
        if order.total_amount < Decimal('0.00'):
            order.total_amount = Decimal('0.00')

    order.save()


def create_order(request):

    if request.method != 'POST':
        return redirect('checkout:checkout')

    payment_method = request.POST.get('payment_method', '').upper()
    address_id = request.POST.get('address_id')

    # 🔒 Validations
    if not payment_method:
        messages.error(request, "Please select payment method")
        return redirect('checkout:checkout')

    if payment_method not in ["COD", "RAZORPAY", "WALLET"]:
        messages.error(request, "Invalid payment method")
        return redirect('checkout:checkout')

    if not address_id:
        messages.error(request, "Please select address")
        return redirect('checkout:checkout')

    address = get_object_or_404(Address, id=address_id, user=request.user)

    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        messages.error(request, "Cart is empty")
        return redirect('cart')

    subtotal = Decimal("0.00")
    delivery_charge = Decimal("0.00")

    # 🛒 Validate items
    for item in cart_items:
        variant = item.variant
        product = variant.product

        subtotal += variant.price * item.quantity

        if not variant.is_active or not product.is_active:
            messages.error(request, f"{product.name} unavailable")
            return redirect("cart")

        if getattr(variant, "is_deleted", False) or getattr(product, "is_deleted", False):
            messages.error(request, f"{product.name} unavailable")
            return redirect("cart")

        if item.quantity > variant.stock:
            messages.error(request, f"Only {variant.stock} items available")
            return redirect("cart")

    # 🎟 Coupon handling (SECURE)
    coupon_code = None
    discount_amount = Decimal("0.00")

    applied_coupon = request.session.get("applied_coupon")

    if applied_coupon:
        coupon = Coupon.objects.filter(
            code=applied_coupon.get("code"),
            is_active=True,
            is_deleted=False
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

    # 💰 Final total
    total_amount = subtotal - discount_amount + delivery_charge

    if total_amount < 0:
        total_amount = Decimal("0.00")

    order_id = f"CLOUZIE-{timezone.now():%y%m%d}-{random.randint(1000,9999)}"

    # 🧾 Create Order
    order = Order.objects.create(
        user=request.user,
        address=address,
        coupon_code=coupon_code,
        order_id=order_id,
        payment_status="PENDING",
        order_status="PENDING",
        subtotal=subtotal,
        discount_amount=discount_amount,
        delivery_charge=delivery_charge,
        payment_method=payment_method,
        total_amount=total_amount,
    )

    # 📦 Create Order Items
    for item in cart_items:
        variant = item.variant

        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name,
            variant_name=f"{variant.size} + {variant.color}",
            price=variant.price,
            quantity=item.quantity,
            total=variant.price * item.quantity,
            status="PENDING",
        )


    if payment_method == "WALLET":

        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        if wallet.balance < total_amount:
            messages.error(request, "Insufficient wallet balance")
            order.delete()
            return redirect('checkout:checkout')

        with transaction.atomic():

            wallet.debit(
                total_amount,
                description="Order payment",
                order=order
            )

            order.payment_status = "PAID"
            order.order_status = "CONFIRMED"
            order.save()

            for item in cart_items:
                variant = item.variant
                variant.stock -= item.quantity
                variant.save()

            cart_items.delete()

            request.session.pop("applied_coupon", None)

        messages.success(request, "Order placed using wallet")
        return redirect('orders:order_success', order_uuid=order.uuid)

    elif payment_method == "COD":

        order.payment_status = "PENDING"
        order.order_status = "PENDING"
        order.save()
        
        for item in cart_items:
            variant = item.variant
            variant.stock -= item.quantity
            variant.save()

        cart_items.delete()
        request.session.pop("applied_coupon", None)

        messages.success(request, "Order placed successfully")
        return redirect('orders:order_success', order_uuid=order.uuid)

    elif payment_method == "RAZORPAY":
        return redirect("checkout:create_razorpay_order")

    return redirect('checkout:checkout')

def create_razorpay_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)

    payment_method = "RAZORPAY"
    address_id = data.get("address_id")

    if not address_id:
        return JsonResponse({"error": "Please select address"}, status=400)

    address = get_object_or_404(Address, id=address_id, user=request.user)

    # 🛒 Get cart items
    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    subtotal = Decimal("0.00")
    delivery_charge = Decimal("0.00")

    # 🧾 Validate items + calculate subtotal
    for item in cart_items:
        variant = item.variant
        product = variant.product

        subtotal += variant.price * item.quantity

        if not variant.is_active:
            return JsonResponse({"error": f"{product.name} unavailable"}, status=400)

        if not product.is_active:
            return JsonResponse({"error": f"{product.name} unavailable"}, status=400)

        if getattr(variant, "is_deleted", False):
            return JsonResponse({"error": f"{product.name} unavailable"}, status=400)

        if getattr(product, "is_deleted", False):
            return JsonResponse({"error": f"{product.name} unavailable"}, status=400)

        if item.quantity > variant.stock:
            return JsonResponse({"error": f"Only {variant.stock} items available"}, status=400)

    # 🎟 Coupon Handling (SECURE)
    coupon_code = None
    discount_amount = Decimal("0.00")

    applied_coupon = request.session.get("applied_coupon")

    if applied_coupon:
        coupon = Coupon.objects.filter(
            code=applied_coupon.get("code"),
            is_active=True,
            is_deleted=False
        ).first()

        if coupon:
            today = timezone.now().date()

            if coupon.start_date <= today <= coupon.end_date:

                if subtotal >= coupon.min_purchase:

                    coupon_code = coupon.code

                    if coupon.discount_type == "PERCENTAGE":
                        discount_amount = (subtotal * coupon.discount_value) / Decimal("100")

                        if coupon.max_discount:
                            discount_amount = min(discount_amount, coupon.max_discount)
                    else:
                        discount_amount = coupon.discount_value

    # 💰 Final amount
    total_amount = subtotal - discount_amount + delivery_charge

    if total_amount < 0:
        total_amount = Decimal("0.00")

    # 🆔 Order ID
    order_id = f"CLOUZIE-{timezone.now():%y%m%d}-{random.randint(1000,9999)}"

    # 🧾 Create Order (PENDING)
    order = Order.objects.create(
        user=request.user,
        address=address,
        coupon_code=coupon_code,
        order_id=order_id,
        payment_method=payment_method,
        payment_status="PENDING",
        order_status="PENDING",
        subtotal=subtotal,
        discount_amount=discount_amount,
        delivery_charge=delivery_charge,
        total_amount=total_amount,
    )

    # 📦 Create Order Items
    for item in cart_items:
        variant = item.variant

        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name,
            variant_name=f"{variant.size} + {variant.color}",
            price=variant.price,
            quantity=item.quantity,
            total=variant.price * item.quantity,
            status="PENDING"
        )

    # 💳 Create Razorpay Order
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    razorpay_order = client.order.create({
        "amount": int(total_amount * 100),  # paisa (NO FLOAT)
        "currency": "INR",
        "payment_capture": "1"
    })

    # 🧠 Store order reference (optional but useful)
    request.session["razorpay_order"] = {
        "order_uuid": str(order.uuid)
    }

    # ❗ DO NOT clear coupon yet (wait for payment success)

    return JsonResponse({
        "key": settings.RAZORPAY_KEY_ID,
        "amount": razorpay_order["amount"],
        "razorpay_order_id": razorpay_order["id"],
        "order_uuid": str(order.uuid)
    })


@login_required
def order_success(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    payment_id = request.GET.get("payment_id")

    # 🔹 Razorpay flow
    if order.payment_method == "RAZORPAY" and order.payment_status == "PENDING":
        order.payment_status = "PAID"
        order.order_status = "PENDING"

        # reduce stock
        for item in order.items.all():
            item.variant.stock -= item.quantity
            item.variant.save()

        # clear cart
        CartItem.objects.filter(cart__user=request.user).delete()

        order.save()

    # 🔹 COD flow
    elif order.payment_method == "COD":
        # already confirmed during order creation
        pass

    return render(request, "checkout/order_success.html", {
        "order": order,
        "payment_id": payment_id
    })


@login_required
def payment_failed(request):
    payment_id = request.GET.get("payment_id")

    return render(request, "checkout/order_failed.html", {
        "payment_id": payment_id
    })

@login_required
def order_management(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').upper()
    sort_by = request.GET.get('sort', 'latest')
    
    orders_list = Order.objects.filter(user=request.user)
    
    if search_query:
        
        orders_list = orders_list.filter(
            models.Q(order_id__icontains=search_query) | 
            models.Q(items__product_name__icontains=search_query)
        ).distinct()
        
    if status_filter in ['PENDING', 'CONFIRMED', 'PACKED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED']:
        orders_list = orders_list.filter(order_status=status_filter)
        
    if sort_by == 'oldest':
        orders_list = orders_list.order_by('placed_at')
    elif sort_by == 'price_high':
        orders_list = orders_list.order_by('-total_amount')
    else:
        orders_list = orders_list.order_by('-placed_at')
        
    paginator = Paginator(orders_list, 10) 
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    
    context = {
        "orders": orders, 
        "search_query": search_query,
        "status_filter": status_filter,
        "sort_by": sort_by
    }
    return render(request, "orders/order_management.html", context)


@login_required
def order_details(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    order_level_return = order.return_requests.filter(order_item__isnull=True).first()
    has_return = (
        order_level_return is not None
        or order.order_status in ('RETURN_REQUESTED', 'RETURNED')
    )

    return_eligible = False
    return_ineligible_reason = ''

    if order.order_status == 'DELIVERED' and not has_return:
        delivered_at = order.delivered_date or order.updated_at
        if timezone.now() <= delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
            return_eligible = True
        else:
            return_ineligible_reason = (
                f'Return window has expired ({RETURN_WINDOW_DAYS} days from delivery).'
            )

    has_partially_cancelled_items = order.order_status == 'PARTIALLY_CANCELLED'

    item_return_eligible_ids = []
    delivered_at = order.delivered_date or order.updated_at
    if delivered_at and timezone.now() <= delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
        item_return_eligible_ids = [
            item.id
            for item in order.items.all()
            if item.status == 'DELIVERED' and not item.return_request.exists()
        ]

    return render(request, 'orders/order_details.html', {
        'order': order,
        'return_eligible': return_eligible,
        'return_ineligible_reason': return_ineligible_reason,
        'has_return': has_return,
        'return_request': order_level_return,
        'has_partially_cancelled_items': has_partially_cancelled_items,
        'item_return_eligible_ids': item_return_eligible_ids,
    })



@login_required
def cancel_order_item(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

        data = json.loads(request.body)
        reason = data.get('reason', '')

        CANCELLABLE_STATUSES = ['PENDING', 'CONFIRMED', 'PACKED']

        if item.status == 'CANCELLED':
            return JsonResponse({'success': False, 'error': 'Item is already cancelled.'})

        if item.status == 'DELIVERED':
            return JsonResponse({'success': False, 'error': 'Delivered items cannot be cancelled. Please use the Return option.'})

        if item.status in ['SHIPPED', 'RETURN_REQUESTED', 'RETURNED']:
            return JsonResponse({'success': False, 'error': 'Item cannot be cancelled at this stage.'})

        if item.status not in CANCELLABLE_STATUSES:
            return JsonResponse({
                "success": False,
                "error": "Item cannot be cancelled at this stage"
            })
            

        item.status = 'CANCELLED'
        item.cancel_reason = reason
        item.save()

        variant = item.variant
        if variant:
            variant.stock += item.quantity
            variant.save()

        update_order_status(item.order)

        return JsonResponse({
            "success": True,
            "message": "Item cancelled successfully"
        })

@login_required
def return_order_item(request, item_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed."})

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    NON_RETURNABLE = [
        'PENDING', 'CONFIRMED', 'PACKED', 'SHIPPED',
        'CANCELLED', 'RETURN_REQUESTED', 'RETURNED',
    ]
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
        order=item.order,
        order_item=item, 
        user=request.user,
        reason=reason,
        notes=notes,
        image=image,
    )

    item.status = 'RETURN_REQUESTED'
    item.save()

    update_order_status(item.order)

    return JsonResponse({"success": True, "message": "Return requested successfully."})


@login_required
def cancel_order(request, order_uuid):
    if request.method != 'POST':
        return redirect('orders:order_details', order_uuid=order_uuid)

    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    CANCELLABLE = ['PENDING', 'CONFIRMED', 'PACKED', 'PARTIALLY_CANCELLED']
    if order.order_status not in CANCELLABLE:
        messages.error(request, "This order cannot be cancelled at its current stage.")
        return redirect('orders:order_details', order_uuid=order_uuid)

    order.order_status = 'CANCELLED'
    for item in order.items.select_related('variant').all():
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()
    order.save()
    messages.success(request, "Order cancelled successfully.")
    return redirect('orders:order_details', order_uuid=order_uuid)

@login_required
def request_return(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid, user=request.user)

    if order.order_status != 'DELIVERED':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('orders:order_details', order_uuid=order_uuid)

    if hasattr(order, 'return_request'):
        messages.error(request, 'A return request already exists for this order.')
        return redirect('orders:order_details', order_uuid=order_uuid)

    delivered_at = order.delivered_date or order.updated_at
    if timezone.now() > delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
        messages.error(request, 'The return window has expired.')
        return redirect('orders:order_details', order_uuid=order_uuid)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        notes  = request.POST.get('notes', '').strip()
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
                   .exclude(status__in=['CANCELLED', 'RETURNED','PARTIALLY_RETURNED','PARTIALLY_CANCELLED'])
    )

    if not items:
        messages.error(request, "No active items to generate invoice for.")
        return redirect('orders:order_details', order_uuid=order_uuid)

    buffer = io.BytesIO()
    PAGE_W, PAGE_H = A4
    ML = 22 * mm   
    MR = 22 * mm   
    MT = 22 * mm  
    MB = 22 * mm 

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
    )

    BLACK   = colors.HexColor('#0a0a0a')
    DGRAY   = colors.HexColor('#555555')
    MGRAY   = colors.HexColor('#999999')
    LGRAY   = colors.HexColor('#dddddd')
    XLIGHT  = colors.HexColor('#f8f8f8')
    WHITE   = colors.white
    W = PAGE_W - ML - MR 

    
    def S(name, size=9, bold=False, color=BLACK, align=TA_LEFT, lead=None, space=0):
        return ParagraphStyle(
            name, fontName='Helvetica-Bold' if bold else 'Helvetica',
            fontSize=size, textColor=color, alignment=align,
            leading=lead or size * 1.5, spaceBefore=space,
        )

    def P(text, style): return Paragraph(text, style)

    def hr(thick=0.4, color=LGRAY, before=0, after=4):
        return HRFlowable(width='100%', thickness=thick, color=color,
                          spaceBefore=before, spaceAfter=after)

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
        ('VALIGN',       (0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',  (0,0),(-1,-1),0),
        ('RIGHTPADDING', (0,0),(-1,-1),0),
        ('TOPPADDING',   (0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(brand_row)
    story.append(Spacer(1, 3 * mm))
    story.append(hr(1.8, BLACK, before=0, after=6))

    placed = order.placed_at.strftime('%d %b %Y')
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
        ('VALIGN',       (0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',  (0,0),(-1,-1),0),
        ('RIGHTPADDING', (0,0),(-1,-1),0),
        ('TOPPADDING',   (0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(meta_row)
    story.append(Spacer(1, 8 * mm))
    story.append(hr(0.4, LGRAY, after=6))

    addr = order.address
    if addr:
        al2 = (f'{addr.address_line2}<br/>' if getattr(addr,'address_line2','') else '')
        bill = (
            f'<b>{addr.full_name}</b><br/>'
            f'{addr.address_line1}<br/>' + al2 +
            f'{addr.city}, {addr.state} - {addr.pincode}<br/>'
            f'India<br/>Ph: {addr.phone_number}'
        )
    else:
        bill = 'No address on record.'

    frm = (
        '<b>CLOUZIE</b><br/>'
        '123 Fashion Street<br/>'
        'Mumbai, Maharashtra - 400001<br/>'
        'India<br/>support@clouzie.com'
    )

    addr_tbl = Table([[
        [P('BILL TO', S('albl', 6.5, True, MGRAY)),
         Spacer(1, 2),
         P(bill, S('av', 8, color=BLACK, lead=13))],
        [P('FROM', S('albl2', 6.5, True, MGRAY)),
         Spacer(1, 2),
         P(frm, S('av2', 8, color=BLACK, lead=13))],
    ]], colWidths=[W * 0.48, W * 0.52])
    addr_tbl.setStyle(TableStyle([
        ('VALIGN',       (0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',  (0,0),(-1,-1),0),
        ('RIGHTPADDING', (0,0),(-1,-1),0),
        ('LEFTPADDING',  (1,0),(1,-1), 6*mm),
        ('LINEAFTER',    (0,0),(0,-1), 0.4, LGRAY),
    ]))
    story.append(addr_tbl)
    story.append(Spacer(1, 8 * mm))
    story.append(hr(0.4, LGRAY, after=4))

    IMG_W = 9 * mm
    IMG_H = 12 * mm
    ROW_H = IMG_H + 4 * mm

    col_w = [IMG_W + 2*mm, None, 28*mm, 12*mm, 22*mm, 22*mm]
    col_w[1] = W - sum(c for c in col_w if c)  

    
    ths = S('th', 7, True, WHITE)
    hrow = [
        P('',          ths),
        P('ITEM',      ths),
        P('SIZE / VAR',ths),
        P('QTY',       S('thc',7,True,WHITE,TA_CENTER)),
        P('PRICE',     S('thr',7,True,WHITE,TA_RIGHT)),
        P('TOTAL',     S('thr2',7,True,WHITE,TA_RIGHT)),
    ]
    table_rows = [hrow]
    row_heights = [8*mm]

    for item in items:
        img_cell = P('', S('e',7))
        has_img = False
        try:
            if item.variant and item.variant.images.first():
                ipath = item.variant.images.first().image.path
                if os.path.exists(ipath):
                    img_cell = RLImage(ipath, width=IMG_W, height=IMG_H)
                    has_img = True
        except Exception:
            pass

        row = [
            img_cell,
            P(item.product_name or '', S('td', 8)),
            P(str(item.variant_name or 'N/A'), S('tdg', 7.5, color=DGRAY)),
            P(str(item.quantity), S('tdc', 8, align=TA_CENTER)),
            P(rs(item.price),     S('tdr', 8, align=TA_RIGHT)),
            P(rs(item.total),     S('tdr2', 8, align=TA_RIGHT)),
        ]
        table_rows.append(row)
        row_heights.append(ROW_H if has_img else 9*mm)

    items_t = Table(table_rows, colWidths=col_w, rowHeights=row_heights, repeatRows=1)
    items_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0), BLACK),
        ('FONTNAME',      (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,0), 7),
        ('TOPPADDING',    (0,0),(-1,0), 8),
        ('BOTTOMPADDING', (0,0),(-1,0), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 5),
        ('RIGHTPADDING',  (0,0),(-1,-1), 5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, XLIGHT]),
        ('FONTNAME',      (0,1),(-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1),(-1,-1), 8),
        ('TOPPADDING',    (0,1),(-1,-1), 4),
        ('BOTTOMPADDING', (0,1),(-1,-1), 4),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('ALIGN',         (3,1),(3,-1),  'CENTER'),
        ('ALIGN',         (4,1),(-1,-1), 'RIGHT'),
        ('LINEBELOW',     (0,0),(-1,-1), 0.25, LGRAY),
        ('BOX',           (0,0),(-1,-1), 0.4,  LGRAY),
    ]))
    story.append(items_t)
    story.append(Spacer(1, 8 * mm))

    sw = 68 * mm
    sum_rows = [['SUBTOTAL', rs(order.subtotal)]]
    if order.discount_amount and order.discount_amount > 0:
        sum_rows.append(['DISCOUNT', '- ' + rs(order.discount_amount)])
    if order.coupon_code:
        sum_rows.append(['COUPON', str(order.coupon_code)])
    sum_rows.append(['SHIPPING', rs(order.delivery_charge) if order.delivery_charge else 'Free'])
    sum_rows.append(['TAX', rs(order.tax_amount)])

    inner = [
        [P(r[0], S(f'sl{i}', 7.5, color=MGRAY)),
         P(r[1],  S(f'sr{i}', 7.5, color=BLACK, align=TA_RIGHT))]
        for i, r in enumerate(sum_rows)
    ] + [[
        P('GRAND TOTAL', S('gl', 9, True, BLACK)),
        P(rs(order.total_amount), S('gr', 9, True, BLACK, TA_RIGHT)),
    ]]
    inner_t = Table(inner, colWidths=[sw * 0.5, sw * 0.5])
    inner_t.setStyle(TableStyle([
        ('TOPPADDING',    (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('LEFTPADDING',   (0,0),(-1,-1), 0),
        ('RIGHTPADDING',  (0,0),(-1,-1), 0),
        ('LINEABOVE',     (0,-1),(-1,-1), 1, BLACK),
        ('TOPPADDING',    (0,-1),(-1,-1), 7),
        ('BOTTOMPADDING', (0,-1),(-1,-1), 7),
    ]))
    outer_t = Table([['', inner_t]], colWidths=[W - sw, sw])
    outer_t.setStyle(TableStyle([
        ('VALIGN',       (0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',  (0,0),(-1,-1),0),
        ('RIGHTPADDING', (0,0),(-1,-1),0),
    ]))
    story.append(outer_t)
    story.append(Spacer(1, 10 * mm))


    story.append(hr(0.4, LGRAY, after=5))
    ft = Table([[
        P('Thank you for shopping with CLOUZIE.', S('ft', 7.5, color=DGRAY)),
        P('Questions?  support@clouzie.com  |  +91 98765 43210',
          S('ft2', 7.5, color=MGRAY, align=TA_RIGHT)),
    ]], colWidths=[W * 0.5, W * 0.5])
    ft.setStyle(TableStyle([
        ('VALIGN',       (0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',  (0,0),(-1,-1),0),
        ('RIGHTPADDING', (0,0),(-1,-1),0),
    ]))
    story.append(ft)
    story.append(Spacer(1, 3 * mm))
    story.append(hr(1.8, BLACK, before=0, after=0))

    doc.build(story)
    buffer.seek(0)

    fname = f'invoice-CLOUZIE-{order.order_id}.pdf'
    resp = HttpResponse(buffer, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{fname}"'
    return resp
