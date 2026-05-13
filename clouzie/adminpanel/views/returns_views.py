from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from orders.models import ReturnRequest, Order, OrderItem
from django.db import transaction
from wallet.models import Wallet
from decimal import Decimal

# ─── Lifecycle ────────────────────────────────────────────────────────────────
# PENDING → APPROVED/REJECTED
# APPROVED → RECEIVED
# RECEIVED → REFUNDED
# REFUNDED → CLOSED (terminal)
# REJECTED → (terminal)

ALLOWED_TRANSITIONS = {
    'PENDING':  ['APPROVED', 'REJECTED'],
    'APPROVED': ['RECEIVED'],
    'RECEIVED': ['REFUNDED'],
    'REFUNDED': [],
    'REJECTED': [],
    'CLOSED':   [],
}

TERMINAL_STATES = {'REJECTED', 'REFUNDED', 'CLOSED'}


def restore_stock(order, order_item=None):
    if order_item:
        if order_item.variant:
            order_item.variant.stock += order_item.quantity
            order_item.variant.save(update_fields=['stock'])
    else:
        for item in order.items.select_related('variant').all():
            if item.variant and item.status not in ['RETURNED', 'CANCELLED']:
                item.variant.stock += item.quantity
                item.variant.save(update_fields=['stock'])


def returns_list(request):
    qs = ReturnRequest.objects.select_related(
        'order', 'user', 'order_item'
    ).order_by('-requested_at')

    search        = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort          = request.GET.get('sort', '').strip()

    if search:
        qs = qs.filter(
            Q(order__order_id__icontains=search)   |
            Q(user__first_name__icontains=search)  |
            Q(user__last_name__icontains=search)   |
            Q(user__email__icontains=search)       |
            Q(user__username__icontains=search)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if sort == 'oldest':
        qs = qs.order_by('requested_at')

    total    = ReturnRequest.objects.count()
    pending  = ReturnRequest.objects.filter(status='PENDING').count()
    approved = ReturnRequest.objects.filter(status='APPROVED').count()
    rejected = ReturnRequest.objects.filter(status='REJECTED').count()
    refunded = ReturnRequest.objects.filter(status='REFUNDED').count()

    paginator = Paginator(qs, 10)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/returns/returns_list.html', {
        'returns':       page_obj,
        'page_obj':      page_obj,
        'total':         total,
        'pending':       pending,
        'approved':      approved,
        'rejected':      rejected,
        'refunded':      refunded,
        'search':        search,
        'status_filter': status_filter,
        'sort':          sort,
    })


def return_detail(request, pk):
    rr = get_object_or_404(
        ReturnRequest.objects.select_related(
            'order', 'order__address', 'user'
        ).prefetch_related('order__items__variant__images'),
        pk=pk
    )
    next_statuses = ALLOWED_TRANSITIONS.get(rr.status, [])
    return render(request, 'adminpanel/returns/return_detail.html', {
        'rr':            rr,
        'next_statuses': next_statuses,
    })


def update_return_status(request, pk):
    if request.method != 'POST':
        return redirect('adminpanel:return_detail', pk=pk)

    rr = get_object_or_404(
        ReturnRequest.objects.select_related('order', 'order_item'),
        pk=pk
    )

    new_status  = request.POST.get('status', '').strip()
    admin_notes = request.POST.get('admin_notes', '').strip()
    order       = rr.order

    # ── Payment safety: never act on an already-refunded order ───────────────
    if order.payment_status == 'REFUNDED' and new_status != 'CLOSED':
        messages.error(request, 'Order is already refunded — no further changes allowed.', extra_tags='toast')
        return redirect('adminpanel:return_detail', pk=pk)

    # ── Validate transition ───────────────────────────────────────────────────
    allowed = ALLOWED_TRANSITIONS.get(rr.status, [])
    if rr.status in TERMINAL_STATES:
        messages.error(request, 'This return request is already finalised.', extra_tags='toast')
        return redirect('adminpanel:return_detail', pk=pk)

    if new_status not in allowed:
        messages.error(request, f'Cannot move from {rr.status} → {new_status}.', extra_tags='toast')
        return redirect('adminpanel:return_detail', pk=pk)

    with transaction.atomic():
        rr.status = new_status
        if admin_notes:
            rr.admin_notes = admin_notes
        rr.save()

        # ── APPROVED: mark item(s) as RETURN_REQUESTED in UI, restore stock ──
        if new_status == 'APPROVED':
            if rr.order_item:
                if rr.order_item.status != 'RETURNED':
                    restore_stock(order, rr.order_item)
                rr.order_item.status = 'RETURN_REQUESTED'
                rr.order_item.save(update_fields=['status'])
            messages.success(request, 'Return approved — awaiting item pickup.', extra_tags='toast')

        # ── RECEIVED: item is back, mark as RETURNED ──────────────────────────
        elif new_status == 'RECEIVED':
            if rr.order_item:
                rr.order_item.status = 'RETURNED'
                rr.order_item.save(update_fields=['status'])
            else:
                order.items.exclude(status='CANCELLED').update(status='RETURNED')

            from orders.views import update_order_status
            update_order_status(order)
            messages.success(request, 'Item received — ready to issue refund.', extra_tags='toast')

        # ── REFUNDED: credit wallet NOW ───────────────────────────────────────

        elif new_status == 'REFUNDED':
            if rr.order_item:
                
                item_value = rr.order_item.price * rr.order_item.quantity

                total_items_value = sum(i.price * i.quantity for i in order.items.all())

            wallet, _ = Wallet.objects.get_or_create(user=order.user)

            discount_total = order.discount_amount or Decimal("0.00")

            if rr.order_item:
                item_value = rr.order_item.price * rr.order_item.quantity

                total_items_value = sum(
                    i.price * i.quantity for i in order.items.all()
                )

                if total_items_value > 0:
                    item_discount = (item_value / total_items_value) * discount_total
                else:
                    item_discount = Decimal("0.00")

                refund_amount = item_value - item_discount

            else:
                total_items_value = sum(
                    i.price * i.quantity for i in order.items.all()
                )

                discount_total = order.discount_amount or Decimal("0.00")

                if total_items_value > 0:
                    refund_amount = total_items_value - discount_total
                else:
                    refund_amount = Decimal("0.00")
            rr.refund_amount = refund_amount
            rr.save(update_fields=['refund_amount'])
            wallet.credit(
                refund_amount,
                description=f"Refund for order {order.order_id}",
                order=order
            )

            messages.success(
                request,
                f'Refund credited to wallet.',
                extra_tags='toast'
            )

        # ── REJECTED ─────────────────────────────────────────────────────────
        elif new_status == 'REJECTED':
            if rr.order_item:
                rr.order_item.status = 'DELIVERED'
                rr.order_item.save(update_fields=['status'])
            else:
                order.order_status = 'DELIVERED'
                order.save(update_fields=['order_status'])

            from orders.views import update_order_status
            update_order_status(order)
            messages.success(request, 'Return request rejected.', extra_tags='toast')

    return redirect('adminpanel:return_detail', pk=pk)