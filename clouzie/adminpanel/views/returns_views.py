from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from orders.models import ReturnRequest, Order
from django.db import transaction
from orders.models import ReturnRequest
from wallet.models import Wallet

def restore_stock(order, order_item=None):
    if order_item:
        if order_item.variant:
            order_item.variant.stock += order_item.quantity
            order_item.variant.save(update_fields=['stock'])
    else:
        for item in order.items.select_related('variant').all():
            if item.variant:
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
            Q(order__order_id__icontains=search) |
            Q(user__first_name__icontains=search)  |
            Q(user__last_name__icontains=search)   |
            Q(user__email__icontains=search)        |
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
    return render(request, 'adminpanel/returns/return_detail.html', {
        'rr':           rr,
    })



def update_return_status(request, pk):
    rr = get_object_or_404(
        ReturnRequest.objects.select_related("order", "order_item"),
        pk=pk
    )

    if request.method != "POST":
        return redirect("adminpanel:return_detail", pk=pk)

    new_status = request.POST.get("status", "").strip()
    admin_notes = request.POST.get("admin_notes", "").strip()

    if rr.status in ["APPROVED", "REJECTED"]:
        messages.error(
            request,
            "Return request already completed.",
            extra_tags="toast"
        )
        return redirect("adminpanel:return_detail", pk=pk)

    if new_status not in ["APPROVED", "REJECTED"]:
        messages.error(
            request,
            "Invalid status selected.",
            extra_tags="toast"
        )
        return redirect("adminpanel:return_detail", pk=pk)

    with transaction.atomic():

        rr.status = new_status
        rr.admin_notes = admin_notes
        rr.save()

        order = rr.order

        if new_status == "APPROVED":
            wallet, _ = Wallet.objects.get_or_create(user=order.user)

            if rr.order_item:
                refund_amount = rr.order_item.total
            else:
                refund_amount = order.total_amount

            wallet.credit(
                refund_amount,
                description=f"Refund for order {order.order_id}",
                order=order
            )
            if rr.order_item:
                if rr.order_item.status != "RETURNED":
                    restore_stock(order, rr.order_item)
                rr.order_item.status = "RETURNED"
                rr.order_item.save(update_fields=["status"])
            else:
                if order.order_status != "RETURNED":
                    restore_stock(order)

            from orders.views import update_order_status
            update_order_status(order)

           
            if order.order_status == "RETURNED" and order.payment_method != "cod":
                order.payment_status = "REFUNDED"
                order.save(update_fields=["payment_status"])

            messages.success(request, "Return approved successfully.", extra_tags="toast")

        elif new_status == "REJECTED":
            if rr.order_item:
                rr.order_item.status = "DELIVERED"
                rr.order_item.save(update_fields=["status"])
            else:
                order.order_status = "DELIVERED"
                order.save(update_fields=["order_status"])

            from orders.views import update_order_status
            update_order_status(order)

            messages.success(request, "Return request rejected.", extra_tags="toast")

    return redirect("adminpanel:return_detail", pk=pk)