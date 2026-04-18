from django.shortcuts import render,get_object_or_404,redirect
from adminpanel.models import Products,Subcategory,Category,Variants
from django.core.paginator import Paginator
from cart.models import Cart,CartItem
from django.http import JsonResponse,HttpResponse
from django.contrib import messages
# Create your views here.
def products_list(request):

    products = Products.objects.filter(is_deleted=False,is_active=True,category__is_active=True,subcategory__is_active=True).prefetch_related("variants__images")
    

    total_count = products.count()
    sub = request.GET.get('sub')
    
    if sub:
        products = Products.objects.filter(subcategory_id=sub,is_deleted=False,is_active=True,category__is_active=True,subcategory__is_active=True)
        
    product_data = []

    for product in products:
        variant = product.variants.filter(is_default=True).first()
        if not variant:
            variant = product.variants.first()

        product_data.append({
            "product": product,
            "variant": variant,
        })
    categoires = get_object_or_404(Category,name='mens')
    subcategories = Subcategory.objects.filter(category_id=categoires.id,is_active=True,category__is_active=True,is_deleted=False,category__is_deleted=False)      
    paginator = Paginator(product_data,8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "products/products_list.html", {
        "product_data": page_obj,
        'page_obj':page_obj,
        "subcategories":subcategories,
        "total_count":total_count,
    })
    
def product_details(request,slug):

    product = get_object_or_404(Products, slug=slug, is_deleted=False,is_active=True)
    variants = product.variants.filter(is_active=True)

    change_variant = request.GET.get('variant')
    is_in_cart = False
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            is_in_cart = CartItem.objects.filter(variant=change_variant).exists()
        except Cart.DoesNotExist:
            pass
    if change_variant:
        default_variant = variants.filter(id=change_variant,is_active=True).first()
    else:
        default_variant = variants.filter(is_default=True).first()

    if not default_variant:
        default_variant = variants.first()
        
    color_variants = variants.filter(color=default_variant.color,is_active=True)

    SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

    sizes = list(
        color_variants.values_list('size', flat=True).distinct()
    )

    sizes.sort(
        key=lambda x: SIZE_ORDER.index(x) if x in SIZE_ORDER else 99
    )

    colors = []
    seen = set()

    for v in variants:
        if v.color not in seen:
            colors.append(v)
            seen.add(v.color)

    return render(request, "products/product_details.html", {
        "product": product,
        "default_variant": default_variant,
        "sizes": sizes,
        "colors": colors,
        "color_variants":color_variants,
        "is_in_cart":is_in_cart,
        "change_variant":change_variant,
    })
    
    
def add_to_cart(request,slug):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
            
            
        variant = get_object_or_404(Variants,id=variant_id)
        
        cart,_= Cart.objects.get_or_create(user=request.user)
        item,created = CartItem.objects.get_or_create(cart=cart,variant=variant)
        variants_id = request.GET.get('variants')
        messages.success(request, "added") 
        request.session['toast_data'] = {
        "product": variant.product.name,
        "price": float(variant.price),
        "size": variant.size,
        "color": variant.color,
        "image": variant.images.first().image.url if variant.images.exists() else ""

            }
        return redirect(f'/products/{slug}?variant={variant_id}')
        


def clear_toast(request):
    print("CLEAR TOAST HIT 🔥")
    request.session.pop('toast_data', None)
    return HttpResponse('hello world')

    

    