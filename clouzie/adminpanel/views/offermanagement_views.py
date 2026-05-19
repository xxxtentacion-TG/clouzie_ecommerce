from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from datetime import datetime
from adminpanel.models import Offer, Products, Category, Subcategory
from django.core.paginator import Paginator

def offer_list(request):
    offers = Offer.objects.filter(is_deleted=False).select_related(
        'product', 'category', 'subcategory'
    ).order_by('-created_at')
    active_count = offers.filter(is_active=True).count()
    inactive_count = offers.filter(is_active=False).count()
    paginator = Paginator(offers,5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'adminpanel/offers/offer_list.html', {
        'page_obj':page_obj,
        'active_count': active_count,
        'inactive_count': inactive_count,
    })


def _get_form_context():
    return {
        'products': Products.objects.filter(is_deleted=False, is_active=True).order_by('name'),
        'categories': Category.objects.filter(is_deleted=False, is_active=True).order_by('name'),
        'subcategories': Subcategory.objects.filter(is_deleted=False, is_active=True).order_by('name'),
    }


def create_offer(request):
    if request.method == 'POST':
        offer_type = request.POST.get('offer_type', '').strip()
        discount_type = request.POST.get('discount_type', '').strip()
        discount_value = request.POST.get('discount_value', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        is_active = 'is_active' in request.POST
        product_id = request.POST.get('product_id') or None
        category_id = request.POST.get('category_id') or None
        subcategory_id = request.POST.get('subcategory_id') or None

        if not all([offer_type, discount_type, discount_value, start_date, end_date]):
            messages.error(request, 'All required fields must be filled.', extra_tags='toast')
            return redirect('adminpanel:create_offer')

        try:
            discount_value_dec = Decimal(discount_value)
            if discount_value_dec <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, 'Invalid discount value.', extra_tags='toast')
            return redirect('adminpanel:create_offer')

        if discount_type == 'PERCENTAGE' and discount_value_dec > 100:
            messages.error(request, 'Percentage discount cannot exceed 100%.', extra_tags='toast')
            return redirect('adminpanel:create_offer')
            
        if discount_type == 'FIXED' and discount_value_dec > 100000:
            messages.error(request, 'Fixed discount cannot exceed 1,00,000.', extra_tags='toast')
            return redirect('adminpanel:create_offer')

        if offer_type == 'PRODUCT' and not product_id:
            messages.error(request, 'Please select a product.', extra_tags='toast')
            return redirect('adminpanel:create_offer')
        elif offer_type == 'CATEGORY' and not category_id:
            messages.error(request, 'Please select a category.', extra_tags='toast')
            return redirect('adminpanel:create_offer')
        elif offer_type == 'SUBCATEGORY' and not subcategory_id:
            messages.error(request, 'Please select a subcategory.', extra_tags='toast')
            return redirect('adminpanel:create_offer')

        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.', extra_tags='toast')
            return redirect('adminpanel:create_offer')

        if start > end:
            messages.error(request, 'End date must be after start date.', extra_tags='toast')
            return redirect('adminpanel:create_offer')

        offer = Offer(
            offer_type=offer_type,
            discount_type=discount_type,
            discount_value=discount_value_dec,
            start_date=start,
            end_date=end,
            is_active=is_active,
        )
        if offer_type == 'PRODUCT' and product_id:
            offer.product_id = product_id
        elif offer_type == 'CATEGORY' and category_id:
            offer.category_id = category_id
        elif offer_type == 'SUBCATEGORY' and subcategory_id:
            offer.subcategory_id = subcategory_id
        offer.save()

        messages.success(request, 'Offer created successfully.', extra_tags='toast')
        return redirect('adminpanel:offer_list')

    ctx = _get_form_context()
    ctx['form_title'] = 'Create Offer'
    ctx['submit_url'] = 'adminpanel:create_offer'
    return render(request, 'adminpanel/offers/offer_form.html', ctx)


def edit_offer(request, pk):
    offer = get_object_or_404(Offer, pk=pk, is_deleted=False)

    if request.method == 'POST':
        offer_type = request.POST.get('offer_type', '').strip()
        discount_type = request.POST.get('discount_type', '').strip()
        discount_value = request.POST.get('discount_value', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        is_active = 'is_active' in request.POST
        product_id = request.POST.get('product_id') or None
        category_id = request.POST.get('category_id') or None
        subcategory_id = request.POST.get('subcategory_id') or None

        if not all([offer_type, discount_type, discount_value, start_date, end_date]):
            messages.error(request, 'All required fields must be filled.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)

        try:
            discount_value_dec = Decimal(discount_value)
            if discount_value_dec <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, 'Invalid discount value.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)

        if discount_type == 'PERCENTAGE' and discount_value_dec > 100:
            messages.error(request, 'Percentage discount cannot exceed 100%.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)

        if discount_type == 'FIXED' and discount_value_dec > 100000:
            messages.error(request, 'Fixed discount cannot exceed 1,00,000.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)

        if offer_type == 'PRODUCT' and not product_id:
            messages.error(request, 'Please select a product.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)
        elif offer_type == 'CATEGORY' and not category_id:
            messages.error(request, 'Please select a category.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)
        elif offer_type == 'SUBCATEGORY' and not subcategory_id:
            messages.error(request, 'Please select a subcategory.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)

        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)

        if start > end:
            messages.error(request, 'End date must be after start date.', extra_tags='toast')
            return redirect('adminpanel:edit_offer', pk=pk)

        offer.offer_type = offer_type
        offer.discount_type = discount_type
        offer.discount_value = discount_value_dec
        offer.start_date = start
        offer.end_date = end
        offer.is_active = is_active
        offer.product_id = None
        offer.category_id = None
        offer.subcategory_id = None

        if offer_type == 'PRODUCT' and product_id:
            offer.product_id = product_id
        elif offer_type == 'CATEGORY' and category_id:
            offer.category_id = category_id
        elif offer_type == 'SUBCATEGORY' and subcategory_id:
            offer.subcategory_id = subcategory_id

        offer.save()
        messages.success(request, 'Offer updated successfully.', extra_tags='toast')
        return redirect('adminpanel:offer_list')

    ctx = _get_form_context()
    ctx['offer'] = offer
    ctx['form_title'] = 'Edit Offer'
    return render(request, 'adminpanel/offers/offer_form.html', ctx)


@require_POST
def delete_offer(request, pk):
    offer = get_object_or_404(Offer, pk=pk, is_deleted=False)
    offer.is_deleted = True
    offer.save(update_fields=['is_deleted'])
    return JsonResponse({'success': True, 'message': 'Offer deleted successfully.'})


@require_POST
def toggle_offer(request, pk):
    offer = get_object_or_404(Offer, pk=pk, is_deleted=False)
    offer.is_active = not offer.is_active
    offer.save(update_fields=['is_active'])
    return JsonResponse({
        'success': True,
        'is_active': offer.is_active,
        'message': f'Offer {"activated" if offer.is_active else "deactivated"} successfully.',
    })
