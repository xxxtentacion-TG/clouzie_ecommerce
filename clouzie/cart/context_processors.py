from .models import Cart, CartItem

def cart_count(request):
    count = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = CartItem.objects.filter(cart=cart).count()
        except:
            count = 0

    return {
        "cart_count": count
    }