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
        item = Wishlist.objects.get(variant__id=id)
        item.delete()
        return redirect(request.META.get('HTTP_REFERER','home_main'))
    
def move_to_cart(request,id):
    if request.method == 'POST':
        wishlist_item = get_object_or_404(Wishlist,user=request.user,variant_id=id)
        variant = wishlist_item.variant
        
        if variant.is_deleted or not variant.is_active or variant.product.is_deleted or not variant.product.is_active:
            messages.error(request, "This item is unavailable.", extra_tags="toast")
            return redirect('wishlist')
        
        if variant.stock <= 0 :
            messages.error(request, "This item is out of stock.", extra_tags="toast")
            return redirect('wishlist')
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item = CartItem.objects.filter(cart=cart,variant=variant).first()
        
        if cart_item:
            limit = min(5, variant.stock)
            if cart_item.quantity >= limit:
                messages.error(request, f"Maximum quantity reached.", extra_tags="toast")
                return redirect('wishlist')
            
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, "Quantity updated in cart", extra_tags="toast")
        else:
            CartItem.objects.create(
                cart=cart,
                variant=variant,
                quantity=1
            )
            messages.success(request, "Moved to bag successfully", extra_tags="toast")
            
        wishlist_item.delete()
        
    return redirect('wishlist')

    
