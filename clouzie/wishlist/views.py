from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from adminpanel.models import Products, Variants
from accounts.models import CustomUser
from .models import Wishlist
from cart.models import Cart, CartItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from utils.offer import get_best_offer


def wishlist(request):

    wishlist = Wishlist.objects.filter(
        user=request.user
    ).select_related(
        "variant",
        "variant__product",
        "variant__product__category",
    ).prefetch_related("variant__images")

    wishlist_items = []

    category_ids = []
    product_ids = []

    for item in wishlist:

        product = item.variant.product

        category_ids.append(product.category_id)
        product_ids.append(product.id)

        base_price = item.variant.price

        final_price, discount, discount_percent = get_best_offer(
            product,
            base_price
        )

        if final_price is None:
            final_price = base_price

        wishlist_items.append({
            "item": item,
            "final_price": final_price,
            "discount": discount,
            "discount_percent": discount_percent,
        })

    suggested_products = Products.objects.filter(
        is_active=True,
        is_deleted=False,
        category_id__in=category_ids,
        variants__is_active=True,
        variants__is_deleted=False,
        variants__stock__gt=0,
    ).exclude(
        id__in=product_ids
    ).prefetch_related(
        "variants__images"
    ).distinct()[:8]

    return render(request, "wishlist/wishlist.html", {
        "wishlist_items": wishlist_items,
        "suggested_products": suggested_products,
    })
    
@login_required
def add_wishlist(request, id):
    variant = get_object_or_404(Variants, id=id)
    item = Wishlist.objects.filter(user=request.user, variant=variant).first()

    if item:
        item.delete()
        wishlisted = False
    else:
        Wishlist.objects.get_or_create(user=request.user, variant=variant)
        wishlisted = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({'wishlisted': wishlisted, 'wishlist_count': count})

    return redirect(request.META.get('HTTP_REFERER', 'home_main'))


def remove_wishlist(request,id):
    if request.method == 'POST':
        item = get_object_or_404(Wishlist, variant__id=id, user=request.user)
        item.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            count = Wishlist.objects.filter(user=request.user).count()
            return JsonResponse({'success': True, 'message': 'Removed from wishlist', 'wishlist_count': count})
        return redirect(request.META.get('HTTP_REFERER','home_main'))
    
def move_to_cart(request,id):
    if request.method == 'POST':
        wishlist_item = get_object_or_404(Wishlist,user=request.user,variant_id=id)
        variant = wishlist_item.variant
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if variant.is_deleted or not variant.is_active or variant.product.is_deleted or not variant.product.is_active:
            if is_ajax: return JsonResponse({'success': False, 'error': 'This item is unavailable.'})
            messages.error(request, "This item is unavailable.", extra_tags="toast")
            return redirect('wishlist')
        
        if variant.stock <= 0 :
            if is_ajax: return JsonResponse({'success': False, 'error': 'This item is out of stock.'})
            messages.error(request, "This item is out of stock.", extra_tags="toast")
            return redirect('wishlist')
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item = CartItem.objects.filter(cart=cart,variant=variant).first()
        
        if cart_item:
            limit = min(5, variant.stock)
            if cart_item.quantity >= limit:
                if is_ajax: return JsonResponse({'success': False, 'error': 'Maximum quantity reached.'})
                messages.error(request, f"Maximum quantity reached.", extra_tags="toast")
                return redirect('wishlist')
            
            cart_item.quantity += 1
            cart_item.save()
            msg = "Quantity updated in cart"
        else:
            CartItem.objects.create(
                cart=cart,
                variant=variant,
                quantity=1
            )
            msg = "Moved to bag successfully"
            
        wishlist_item.delete()
        
        if is_ajax:
            cart_count = CartItem.objects.filter(cart=cart).count()
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            toast_data = {
                "image": variant.images.first().image.url if variant.images.exists() else "",
                "product": variant.product.name,
                "price": str(variant.price),
                "color": variant.color or "Standard",
                "size": variant.size or "One Size",
            }
            return JsonResponse({
                "success": True, 
                "message": msg,
                "cart_count": cart_count,
                "wishlist_count": wishlist_count,
                "toast_data": toast_data
            })
            
        messages.success(request, msg, extra_tags="toast")
        
    return redirect('wishlist')

