from django.shortcuts import render, redirect, get_object_or_404
from orders.models import OrderItem, Order
from django.core.paginator import Paginator
from django.contrib import messages
from adminpanel.utils.admin_gaurd import admin_required


STOCK_RESTORE_ON = {'CANCELLED', 'RETURNED'}


ALLOWED_TRANSITIONS = {
    'PENDING':          ['CONFIRMED', 'CANCELLED'],
    'CONFIRMED':        ['PACKED', 'CANCELLED'],
    'PACKED':           ['SHIPPED', 'CANCELLED'],
    'SHIPPED':          ['DELIVERED'],
    'DELIVERED':        ['RETURN_REQUESTED'],
    'PARTIALLY_CANCELLED': ['PACKED', 'SHIPPED', 'DELIVERED', 'CANCELLED'],
    'RETURN_REQUESTED': ['RETURNED', 'CANCELLED'],
    'CANCELLED':        [],
    'RETURNED':         [],
    'REJECTED':         [],
}

PAYMENT_TRANSITIONS = {
    'PENDING':            ['PAID', 'FAILED'],
    'PAID':               ['REFUNDED'],          
    'FAILED':             ['PENDING'],            
    'REFUNDED':           [],                     
    'PARTIALLY_REFUNDED': ['REFUNDED'],           
}
FINAL_STATES = {'CANCELLED', 'RETURNED', 'REJECTED'}


def restore_stock(order):
    for item in order.items.select_related('variant').all():
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=['stock'])

@admin_required
def orders_list(request):
    qs = Order.objects.select_related('user').all().order_by('-placed_at')
    status = request.GET.get('status')
    payment = request.GET.get('payment')
    sort = request.GET.get('sort')
    if status:
        qs = qs.filter(order_status=status)
        
    if payment:
        qs = qs.filter(payment_status=payment)
        
    if sort:
        qs = qs.order_by(sort)
            
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'adminpanel/orders/orders_list.html', {
        'orders': page_obj, 'page_obj': page_obj
    })

@admin_required
def order_details(request, uuid):
    order = get_object_or_404(Order.objects.prefetch_related('items'), uuid=uuid)
    active_count = sum(1 for i in order.items.all() if i.status != 'CANCELLED')
    cancelled_count = len(order.items.all()) - active_count
    return render(request, 'adminpanel/orders/order_details.html', {
        'order': order,
        'active_count': active_count,
        'cancelled_count': cancelled_count,
    })

@admin_required
def order_status(request, id):
    order = get_object_or_404(Order, id=id)

    if request.method != 'POST':
        return redirect('adminpanel:order_details', order.uuid)

    current        = order.order_status
    new_status     = request.POST.get('order_status', '').strip()
    payment_status = request.POST.get('payment_status', '').strip()

    # ── ORDER STATUS ──────────────────────────────────────────────────
    if new_status and new_status != current:

        if current in FINAL_STATES:
            messages.error(request,
                'This order is finalised — no further changes allowed.',
                extra_tags='toast')
            return redirect('adminpanel:order_details', order.uuid)

        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            messages.error(request,
                f'Cannot change order status from {current} → {new_status}.',
                extra_tags='toast')
            return redirect('adminpanel:order_details', order.uuid)

        if new_status in STOCK_RESTORE_ON and current not in STOCK_RESTORE_ON:
            restore_stock(order)

        order.order_status = new_status

        for item in order.items.all():
            if new_status == 'RETURNED' and item.status == 'RETURN_REQUESTED':
                item.status = 'RETURNED'
                item.save()
            elif new_status == 'CANCELLED' and item.status not in ['CANCELLED', 'RETURNED', 'DELIVERED']:
                item.status = 'CANCELLED'
                item.save()

    # ── PAYMENT STATUS ────────────────────────────────────────────────
    if payment_status and payment_status != order.payment_status:

        allowed_payment = PAYMENT_TRANSITIONS.get(order.payment_status, [])

        if not allowed_payment:
            messages.error(request,
                f'Payment status is finalised ({order.payment_status}) — no further changes allowed.',
                extra_tags='toast')
            return redirect('adminpanel:order_details', order.uuid)

        if payment_status not in allowed_payment:
            messages.error(request,
                f'Cannot change payment from {order.payment_status} → {payment_status}. '
                f'Allowed: {", ".join(allowed_payment)}.',
                extra_tags='toast')
            return redirect('adminpanel:order_details', order.uuid)

        order.payment_status = payment_status

    # ── SAVE ONCE ─────────────────────────────────────────────────────
    order.save()
    messages.success(request, 'Order updated successfully.', extra_tags='toast')
    return redirect('adminpanel:order_details', order.uuid)