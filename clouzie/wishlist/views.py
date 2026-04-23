from django.shortcuts import render,get_object_or_404,redirect
from adminpanel.models import Variants
from accounts.models import CustomUser
from .models import Wishlist
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
