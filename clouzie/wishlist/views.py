from django.shortcuts import render,get_object_or_404,redirect
from adminpanel.models import Variants
from accounts.models import CustomUser
from .models import Wishlist
from cart.models import Cart,CartItem
from django.contrib import messages
# Create your views here.
def wishlist(request):
    wishlist = Wishlist.objects.filter(user=request.user)
    return render(request,"wishlist/wishlist.html",{"wishlist_items":wishlist})

def add_wishlist(request,id):
    variant = get_object_or_404(Variants,id=id) 
    item = Wishlist.objects.filter(user=request.user,variant=variant).first()
    if item:
        item.delete()
    else:    
        Wishlist.objects.get_or_create(
            user=request.user,
            variant=variant,
        )
    return redirect(request.META.get('HTTP_REFERER','home_main'))

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

    
