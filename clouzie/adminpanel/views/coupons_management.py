from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from adminpanel.models import Coupon
from decimal import Decimal

from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from datetime import datetime
from adminpanel.models import Coupon


def coupon_management(request):
    coupons = Coupon.objects.filter(is_deleted=False).order_by('-created_at')
    active_count = coupons.filter(is_active=True).count()
    inactive_count = coupons.filter(is_active=False).count()

    if request.method == 'POST':

        code = request.POST.get('code', '').strip().upper()
        discount_type = request.POST.get('discount_type')

        discount_value = request.POST.get('discount_value')
        min_purchase = request.POST.get('min_purchase')
        max_discount = request.POST.get('max_discount')
        usage_limit = request.POST.get('usage_limit')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        is_active = 'is_active' in request.POST

        if not code or not discount_type or not discount_value or not min_purchase:
            messages.error(request, "All required fields must be filled.")
            return redirect('adminpanel:coupons')

        if Coupon.objects.filter(code=code).exists():
            messages.error(request, "Coupon code already exists.")
            return redirect('adminpanel:coupons')
        
        try:
            discount_value = Decimal(discount_value)
            min_purchase = Decimal(min_purchase)
            max_discount = Decimal(max_discount) if max_discount else None
        except InvalidOperation:
            messages.error(request, "Invalid numeric values.")
            return redirect('adminpanel:coupons')

        if discount_value <= 0 or min_purchase < 0:
            messages.error(request, "Values must be positive.")
            return redirect('adminpanel:coupons')

        if discount_type == "PERCENTAGE":
            if discount_value > 100:
                messages.error(request, "Percentage cannot exceed 100.")
                return redirect('adminpanel:coupons')
            if not max_discount:
                messages.error(request, "Max discount required for percentage.")
                return redirect('adminpanel:coupons')
        else:
            max_discount = None

        try:
            usage_limit = int(usage_limit) if usage_limit else None
            if usage_limit is not None and usage_limit < 1:
                raise ValueError
        except ValueError:
            messages.error(request, "Invalid usage limit.")
            return redirect('adminpanel:coupons')

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except:
            messages.error(request, "Invalid date format.")
            return redirect('adminpanel:coupons')

        if start_date_obj > end_date_obj:
            messages.error(request, "End date must be after start date.")
            return redirect('adminpanel:coupons')

        Coupon.objects.create(
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            min_purchase=min_purchase,
            max_discount=max_discount,
            usage_limit_per_user=usage_limit,
            start_date=start_date_obj,
            end_date=end_date_obj,
            is_active=is_active
        )

        messages.success(request, "Coupon created successfully.")
        return redirect('adminpanel:coupons')

    return render(request, "adminpanel/coupons/coupon_list.html", {
        "coupons": coupons,
        "active_count": active_count,
        "inactive_count": inactive_count
    })
    
    
def edit_coupon(request):
    if request.method == 'POST':
        coupon_id = request.POST.get('coupon_id')
        coupon = get_object_or_404(Coupon, id=coupon_id)

        code = request.POST.get('code', '').strip().upper()
        discount_type = request.POST.get('discount_type')

        discount_value = request.POST.get('discount_value')
        min_purchase = request.POST.get('min_purchase')
        max_discount = request.POST.get('max_discount')
        usage_limit = request.POST.get('usage_limit')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        is_active = 'is_active' in request.POST

        if not code or not discount_type or not discount_value or not min_purchase:
            messages.error(request, "All required fields must be filled.")
            return redirect('adminpanel:coupons')

        if Coupon.objects.filter(code=code).exclude(id=coupon_id).exists():
            messages.error(request, "Coupon code already exists.")
            return redirect('adminpanel:coupons')

        try:
            discount_value = Decimal(discount_value)
            min_purchase = Decimal(min_purchase)
            max_discount = Decimal(max_discount) if max_discount else None
        except:
            messages.error(request, "Invalid numeric values.")
            return redirect('adminpanel:coupons')

        if discount_type == "PERCENTAGE" and discount_value > 100:
            messages.error(request, "Percentage cannot exceed 100.")
            return redirect('adminpanel:coupons')

        try:
            usage_limit = int(usage_limit) if usage_limit else None
        except:
            messages.error(request, "Invalid usage limit.")
            return redirect('adminpanel:coupons')

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start_date > end_date:
            messages.error(request, "End date must be after start date.")
            return redirect('adminpanel:coupons')

        coupon.code = code
        coupon.discount_type = discount_type
        coupon.discount_value = discount_value
        coupon.min_purchase = min_purchase
        coupon.max_discount = max_discount
        coupon.usage_limit_per_user = usage_limit
        coupon.start_date = start_date
        coupon.end_date = end_date
        coupon.is_active = is_active

        coupon.save()
        messages.success(request, "Coupon updated successfully.")
        return redirect('adminpanel:coupons')

    return redirect('adminpanel:coupons')

def delete_coupon(request):
    if request.method == 'POST':
        coupon_id = request.POST.get('coupon_id')
        coupon = get_object_or_404(Coupon, id=coupon_id)

        coupon.is_deleted = True
        coupon.save()

        messages.success(request, "Coupon deleted successfully.")
        return redirect('adminpanel:coupons')

    return redirect('adminpanel:coupons')