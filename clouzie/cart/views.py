from django.shortcuts import render,get_object_or_404,redirect
from adminpanel.models import Products,Subcategory,Category,Variants
from django.core.paginator import Paginator
from django.http import JsonResponse,HttpResponse
from django.contrib import messages
from cart.models import Cart,CartItem
from accounts.models import CustomUser
from django.db.models import Sum,F
# def add_to_cart(request,slug):
#     if request.method == 'POST':
#         variant_id = request.POST.get('variant_id')
#         variant = get_object_or_404(Variants,id=variant_id)
        
#         cart,_= Cart.objects.get_or_create(user=request.user)
#         item,created = CartItem.objects.get_or_create(cart=cart,variant=variant)
#         variants_id = request.GET.get('variants')
#         if variant_id:
#             messages.success(request, "added") 

#             request.session['toast_data'] = {

#             "product": variant.product.name,

#             "price": float(variant.price),

#             "size": variant.size,

#             "color": variant.color,

#             "image": variant.images.first().image.url if variant.images.exists() else ""

#                 }
#             return redirect(f'/products/{slug}?variant={variant_id}')
#         else:
#             messages.success(request, "added")

#             request.session['toast_data'] = {

#             "product": variant.product.name,

#             "price": float(variant.price),

#             "size": variant.size,

#             "color": variant.color,

#             "image": variant.images.first().image.url if variant.images.exists() else ""

#                 }
#             return redirect(f'/products/{slug}')
        


# def clear_toast(request):
#     print("CLEAR TOAST HIT 🔥")
#     request.session.pop('toast_data', None)
#     return HttpResponse('hello world')

def get_cart_totals(user):
    cart = Cart.objects.get(user=user)
    cart_items = CartItem.objects.filter(cart=cart)
    if not cart_items.exists():
        return {"sub_total": 0, "delivery_charge": 0, "grand_total": 0}
        
    sub_total = cart_items.aggregate(total=Sum(F('variant__price') * F('quantity')))['total'] or 0
    delivery_charge = 0 if sub_total > 1999 else 99
    grand_total = sub_total + delivery_charge
    return {
        "sub_total": sub_total,
        "delivery_charge": delivery_charge,
        "grand_total": grand_total
    }

def cart(request):
    user_id = request.user.id
    user_obj = get_object_or_404(CustomUser,id=user_id)
    cart = Cart.objects.get(user=user_obj)
    cart_items = CartItem.objects.filter(cart=cart).order_by('-variant_id')
    sub_total = cart_items.aggregate(total=Sum(F('variant__price') * F('quantity')))['total'] or 0
    if cart_items.exists():
        if sub_total > 1999:
            delivery_charge = 0
        else:
            delivery_charge = 99
    else:
        delivery_charge = 0
    grand_total = sub_total + delivery_charge
    
    return render(request,"cart/cart.html",{"cart_items":cart_items,"sub_total":sub_total,"delivery_charge":delivery_charge,"grand_total":grand_total})

def increase(request,id):
    item = get_object_or_404(CartItem,id=id,cart__user=request.user)
    if item.quantity >=5:
        return JsonResponse({
            "success":False,
            "message":"Only 5 items allowed"
        })
        
    item.quantity +=1
    item.save()
    
    totals = get_cart_totals(request.user)
    return JsonResponse({
        "success":True,
        "quantity":item.quantity,
        **totals
    })
    
def decrease(request,id):
    item = get_object_or_404(CartItem,id=id,cart__user=request.user)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
        
        totals = get_cart_totals(request.user)
        return JsonResponse({
            "success":True,
            "quantity":item.quantity,
            **totals
        })
    else:
        return JsonResponse({"success":False, "message":"Quantity cannot be less than 1"})

def remove_item(request,id):
    item = get_object_or_404(CartItem,id=id,cart__user=request.user)
    item.delete()
    
    totals = get_cart_totals(request.user)
    return JsonResponse({
        "success":True,
        **totals
    })


    

    