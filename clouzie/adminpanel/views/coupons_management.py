from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from adminpanel.models import Coupon
from decimal import Decimal

from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from datetime import datetime
from adminpanel.models import Coupon
from django.core.paginator import Paginator


def coupon_management(request):
    coupons = Coupon.objects.filter(is_deleted=False).order_by('-created_at')
    active_count = coupons.filter(is_active=True).count()
    inactive_count = coupons.filter(is_active=False).count()
    
    if request.method == 'POST':

        code = request.POST.get('code', '').replace(' ', '').strip().upper()
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
            
        if code.isdigit():
            messages.error(request, "Coupon code cannot contain only numbers.")
            return redirect('adminpanel:coupons')
        
        try:
            discount_value = Decimal(discount_value)
            min_purchase = Decimal(min_purchase)
            max_discount = Decimal(max_discount) if max_discount else None
        except InvalidOperation:
            messages.error(request, "Invalid numeric values.")
            return redirect('adminpanel:coupons')


        if discount_type == "PERCENTAGE":
            if discount_value <= 0 or discount_value > 100:
                messages.error(request, "Percentage discount must be between 1 and 100.")
                return redirect('adminpanel:coupons')
            if not max_discount:
                messages.error(request, "Max discount is required for percentage type.")
                return redirect('adminpanel:coupons')
            if max_discount <= 0:
                messages.error(request, "Max discount must be greater than 0.")
                return redirect('adminpanel:coupons')
        else:
            if discount_value <= 0 or discount_value > 100000:
                messages.error(request, "Fixed discount must be between 1 and 1,00,000.")
                return redirect('adminpanel:coupons')
            max_discount = None

        if min_purchase < 0 or min_purchase > 1000000:
            messages.error(request, "Minimum purchase must be between 0 and 10,00,000.")
            return redirect('adminpanel:coupons')

        if usage_limit:
            try:
                usage_limit = int(usage_limit)
                if usage_limit < 1 or usage_limit > 1000:
                    messages.error(request, "Usage limit must be between 1 and 1000.")
                    return redirect('adminpanel:coupons')
            except ValueError:
                messages.error(request, "Usage limit must be a whole number.")
                return redirect('adminpanel:coupons')
        else:
            usage_limit = None

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
    paginator = Paginator(coupons,5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "adminpanel/coupons/coupon_list.html", {
        'page_obj':page_obj,
        "active_count": active_count,
        "inactive_count": inactive_count
    })
    
    
def edit_coupon(request):
    if request.method == 'POST':
        coupon_id = request.POST.get('coupon_id')
        coupon = get_object_or_404(Coupon, id=coupon_id)

        code = request.POST.get('code', '').replace(' ', '').strip().upper()
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

        if code.isdigit():
            messages.error(request, "Coupon code cannot contain only numbers.")
            return redirect('adminpanel:coupons')

        try:
            discount_value = Decimal(discount_value)
            min_purchase = Decimal(min_purchase)
            max_discount = Decimal(max_discount) if max_discount else None
        except:
            messages.error(request, "Invalid numeric values.")
            return redirect('adminpanel:coupons')

        if discount_type == "PERCENTAGE":
            if discount_value <= 0 or discount_value > 100:
                messages.error(request, "Percentage discount must be between 1 and 100.")
                return redirect('adminpanel:coupons')
            if not max_discount:
                messages.error(request, "Max discount is required for percentage type.")
                return redirect('adminpanel:coupons')
            if max_discount <= 0:
                messages.error(request, "Max discount must be greater than 0.")
                return redirect('adminpanel:coupons')
        else:
            if discount_value <= 0 or discount_value > 100000:
                messages.error(request, "Fixed discount must be between 1 and 1,00,000.")
                return redirect('adminpanel:coupons')
            max_discount = None

        if min_purchase < 0 or min_purchase > 1000000:
            messages.error(request, "Minimum purchase must be between 0 and 10,00,000.")
            return redirect('adminpanel:coupons')

        if usage_limit:
            try:
                usage_limit = int(usage_limit)
                if usage_limit < 1 or usage_limit > 1000:
                    messages.error(request, "Usage limit must be between 1 and 1000.")
                    return redirect('adminpanel:coupons')
            except ValueError:
                messages.error(request, "Usage limit must be a whole number.")
                return redirect('adminpanel:coupons')
        else:
            usage_limit = None

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except:
            messages.error(request, "Invalid date format.")
            return redirect('adminpanel:coupons')

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