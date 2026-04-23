from .models import Wishlist

def wishlist_count(request):
    count = 0

    if request.user.is_authenticated:
        count = Wishlist.objects.filter(user=request.user).count()

    return {
        'wishlist_count': count
    }