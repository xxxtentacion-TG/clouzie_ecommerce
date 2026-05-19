from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from orders.models import ReturnRequest, Order, OrderItem
from django.db import transaction
from wallet.models import Wallet
from decimal import Decimal

ALLOWED_TRANSITIONS = {
    'PENDING':  ['APPROVED', 'REJECTED'],
    'APPROVED': ['RECEIVED'],
    'RECEIVED': ['REFUNDED'],
    'REFUNDED': [],
    'REJECTED': [],
    'CLOSED':   [],
}

TERMINAL_STATES   = frozenset({'REJECTED', 'REFUNDED', 'CLOSED'})
EXCLUDED_STATUSES = frozenset({'CANCELLED', 'RETURNED'})


# ─── Refund calculator ────────────────────────────────────────────────────────

def _proportional_refund(item_value, subtotal_base, original_coupon):
    """
    item_value       — item.price × item.quantity  (post-offer, pre-coupon)
    subtotal_base    — sum of active item values at the time of this refund
                       (must INCLUDE the item being refunded)
    original_coupon  — order.discount_amount snapshotted before any mutation
    """
    if subtotal_base > 0 and original_coupon > 0:
        coupon_share = (item_value / subtotal_base) * original_coupon
    else:
        coupon_share = Decimal("0.00")
    return max(item_value - coupon_share, Decimal("0.00"))


def calculate_refund_amount(order, order_item=None):
    """
    Calculate the correct refund for a return.
    Uses order.coupon_discount — the original immutable coupon — so the
    proportional split is always correct regardless of prior mutations.
    """
    # Always use the original coupon, never the mutated discount_amount
    original_coupon = order.coupon_discount or Decimal("0.00")

    active_items    = order.items.exclude(status__in=EXCLUDED_STATUSES)
    active_subtotal = sum(
        i.price * i.quantity for i in active_items
    ) or Decimal("0.00")

    if order_item:
        item_value    = order_item.price * order_item.quantity
        refund_amount = _proportional_refund(item_value, active_subtotal, original_coupon)
    else:
        # Whole-order return: full active value minus coupon, plus tax/delivery
        refund_amount = max(active_subtotal - original_coupon, Decimal("0.00"))
        refund_amount += (order.tax_amount      or Decimal("0.00"))
        refund_amount += (order.delivery_charge or Decimal("0.00"))

    return max(refund_amount, Decimal("0.00"))


# ─── Stock helpers ────────────────────────────────────────────────────────────

def restore_stock(order, order_item=None):
    if order_item:
        if order_item.variant:
            order_item.variant.stock += order_item.quantity
            order_item.variant.save(update_fields=['stock'])
    else:
        for item in order.items.select_related('variant').exclude(status__in=EXCLUDED_STATUSES):
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save(update_fields=['stock'])


def reverse_stock(order, order_item=None):
    """Undo a stock restore — used when APPROVED → REJECTED."""
    if order_item:
        if order_item.variant:
            order_item.variant.stock -= order_item.quantity
            order_item.variant.save(update_fields=['stock'])
    else:
        for item in order.items.select_related('variant').filter(status='RETURN_REQUESTED'):
            if item.variant:
                item.variant.stock -= item.quantity
                item.variant.save(update_fields=['stock'])


# ─── Views ────────────────────────────────────────────────────────────────────

def returns_list(request):
    qs = ReturnRequest.objects.select_related(
        'order', 'user', 'order_item'
    ).order_by('-requested_at')

    search        = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort          = request.GET.get('sort', '').strip()

    if search:
        qs = qs.filter(
            Q(order__order_id__icontains=search)  |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)  |
            Q(user__email__icontains=search)      |
            Q(user__username__icontains=search)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if sort == 'oldest':
        qs = qs.order_by('requested_at')

    base = ReturnRequest.objects
    paginator = Paginator(qs, 10)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/returns/returns_list.html', {
        'returns':       page_obj,
        'page_obj':      page_obj,
        'total':         base.count(),
        'pending':       base.filter(status='PENDING').count(),
        'approved':      base.filter(status='APPROVED').count(),
        'rejected':      base.filter(status='REJECTED').count(),
        'refunded':      base.filter(status='REFUNDED').count(),
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
    return render(request, 'adminpanel/returns/return_detail.html', {
        'rr':            rr,
        'next_statuses': ALLOWED_TRANSITIONS.get(rr.status, []),
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

    # ── Guards ────────────────────────────────────────────────────────────────
    if rr.status in TERMINAL_STATES:
        messages.error(request, 'This return request is already finalised.', extra_tags='toast')
        return redirect('adminpanel:return_detail', pk=pk)

    if order.payment_status == 'REFUNDED' and new_status == 'REFUNDED':
        messages.error(request, 'Order is already refunded — cannot issue a second refund.', extra_tags='toast')
        return redirect('adminpanel:return_detail', pk=pk)

    if new_status not in ALLOWED_TRANSITIONS.get(rr.status, []):
        messages.error(request, f'Cannot move from {rr.status} → {new_status}.', extra_tags='toast')
        return redirect('adminpanel:return_detail', pk=pk)

    with transaction.atomic():
        rr.status = new_status
        if admin_notes:
            rr.admin_notes = admin_notes
        rr.save()

        # ── APPROVED ──────────────────────────────────────────────────────────
        if new_status == 'APPROVED':
            if rr.order_item:
                if rr.order_item.status not in EXCLUDED_STATUSES:
                    restore_stock(order, rr.order_item)
                rr.order_item.status = 'RETURN_REQUESTED'
                rr.order_item.save(update_fields=['status'])
            else:
                restore_stock(order)
                order.items.exclude(status__in=EXCLUDED_STATUSES).update(status='RETURN_REQUESTED')

            messages.success(request, 'Return approved — awaiting item pickup.', extra_tags='toast')

        # ── RECEIVED ──────────────────────────────────────────────────────────
        elif new_status == 'RECEIVED':
            if rr.order_item:
                rr.order_item.status = 'RETURNED'
                rr.order_item.save(update_fields=['status'])
            else:
                order.items.exclude(status='CANCELLED').update(status='RETURNED')

            from orders.views import update_order_status
            update_order_status(order)
            messages.success(request, 'Item received — ready to issue refund.', extra_tags='toast')

        # ── REFUNDED ──────────────────────────────────────────────────────────
        elif new_status == 'REFUNDED':

            if rr.refund_amount:
                messages.error(request, 'Refund already processed.', extra_tags='toast')
                return redirect('adminpanel:return_detail', pk=pk)

            # Always use the original coupon — discount_amount is already mutated
            original_coupon   = order.coupon_discount   or Decimal("0.00")
            original_subtotal = order.original_subtotal or order.subtotal or Decimal("1.00")

            if rr.order_item:
                item_value = rr.order_item.price * rr.order_item.quantity

                # Coupon share is ALWAYS item_value / original_subtotal × original_coupon
                # — fixed proportion set at order creation, never shifts with cancellations
                refund_amount = _proportional_refund(
                    item_value, original_subtotal, original_coupon
                )
                description = f"Refund for returned item in order {order.order_id}"

            else:
                # Whole-order return: sum of all non-cancelled items (now RETURNED)
                all_items   = order.items.exclude(status='CANCELLED')
                total_value = sum(i.price * i.quantity for i in all_items) or Decimal("0.00")

                # Deduct only the proportional coupon share for these items
                coupon_to_deduct = (total_value / original_subtotal) * original_coupon
                refund_amount    = max(total_value - coupon_to_deduct, Decimal("0.00"))
                refund_amount   += (order.tax_amount      or Decimal("0.00"))
                refund_amount   += (order.delivery_charge or Decimal("0.00"))
                description = f"Refund for returned order {order.order_id}"

            refund_amount = max(refund_amount, Decimal("0.00"))

            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.credit(
                refund_amount,
                description=description,
                order=order,
            )

            rr.refund_amount = refund_amount

            remaining_items = order.items.exclude(status__in=EXCLUDED_STATUSES)

            if not remaining_items.exists():
                order.payment_status = 'REFUNDED'
            else:
                order.payment_status = 'PARTIALLY_REFUNDED'

            rr.save(update_fields=['refund_amount'])
            order.save(update_fields=['payment_status'])

            messages.success(request, f'₹{refund_amount} refund credited to wallet.', extra_tags='toast')

        # ── REJECTED ──────────────────────────────────────────────────────────
        elif new_status == 'REJECTED':
            if rr.order_item:
                if rr.order_item.status == 'RETURN_REQUESTED':
                    reverse_stock(order, rr.order_item)
                rr.order_item.status = 'DELIVERED'
                rr.order_item.save(update_fields=['status'])
            else:
                reverse_stock(order)
                order.items.filter(status='RETURN_REQUESTED').update(status='DELIVERED')
                order.order_status = 'DELIVERED'
                order.save(update_fields=['order_status'])

            from orders.views import update_order_status
            update_order_status(order)
            messages.success(request, 'Return request rejected.', extra_tags='toast')

    return redirect('adminpanel:return_detail', pk=pk)