from django.shortcuts import render,get_object_or_404,redirect
from adminpanel.models import Products,Subcategory,Category,Variants
from django.core.paginator import Paginator
from cart.models import Cart,CartItem
from django.http import JsonResponse,HttpResponse
from django.contrib import messages
from wishlist.models import Wishlist
from django.db.models import Min,Count,Q,Avg
from utils.offer import get_best_offer
from decimal import Decimal
from reviews.models import Review
from orders.models import OrderItem
def products_list(request):

    products = Products.objects.filter(is_deleted=False,is_active=True,category__is_active=True,subcategory__is_active=True).prefetch_related("variants__images")
    
    sub = request.GET.get('sub')
    subcategory = request.GET.getlist('category')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    sort = request.GET.get('sort')
    search = request.GET.get('q','').strip().lower()
    
    if sub:
        products = Products.objects.filter(subcategory_id=sub,is_deleted=False,is_active=True,category__is_active=True,subcategory__is_active=True)
        
    if subcategory and "all" not in subcategory:
        products = products.filter(subcategory__name__in=subcategory)

        
    if search:
        if search in ['shirts','shirt','plain shirt']:
            products = products.filter(Q(name__iexact="shirt") | Q(subcategory__name__iexact="shirts"))
        elif search in ["pant","pants","linen pant"]:
            products = products.filter(Q(name__iexact="pant") | Q(subcategory__name__iexact="pants"))
        elif search in ["tshirt", "t-shirt", "tee","tshirts"]:
            products = products.filter(Q(name__icontains="tshirt") | Q(subcategory__name__icontains="tshirt"))
        else:
            products = products.filter(name__icontains=search)
          
    products = products.annotate(min_price=Min('variants__price')).order_by('-id')
    
    product_data = []

    for product in products:
        variant = product.variants.filter(is_active=True, is_deleted=False)
        variant = variant.filter(is_default=True).order_by('price').first()

        if not variant:
            variant = product.variants.filter(is_active=True, is_deleted=False).first()

        if variant:
            base_price = variant.price
            final_price, discount, discount_percent = get_best_offer(product, base_price)

            product_data.append({
                "product": product,
                "variant": variant,
                "final_price": final_price,
                "discount": discount,
                'discount_percent': discount_percent,
            })

    # ✅ Filter by final_price AFTER offers are applied
    if price_min:
        product_data = [p for p in product_data if p['final_price'] >= Decimal(price_min)]
    if price_max:
        product_data = [p for p in product_data if p['final_price'] <= Decimal(price_max)]

    # ✅ total_count after all filters
    total_count = len(product_data)

    if sort == 'price_asc':
        product_data.sort(key=lambda x: x['final_price'])
    elif sort == 'price_desc':
        product_data.sort(key=lambda x: x['final_price'], reverse=True)
    elif sort == 'a_z':
        product_data.sort(key=lambda x: x['product'].name.lower())
    elif sort == 'z_a':
        product_data.sort(key=lambda x: x['product'].name.lower(), reverse=True)
    
    categoires = get_object_or_404(Category,name='mens')
    subcategories = Subcategory.objects.filter(category_id=categoires.id,is_active=True,category__is_active=True,is_deleted=False,category__is_deleted=False).annotate(active_count=Count('products',filter=Q(products__is_active=True,products__is_deleted=False)))     
    
    paginator = Paginator(product_data, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()

    sub_query = request.GET.copy()
    if 'sub' in sub_query:
        del sub_query['sub']
    if 'page' in sub_query:
        del sub_query['page']
    sub_query_string = sub_query.urlencode()

    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist_variant_ids = list(Wishlist.objects.filter(user=request.user).values_list('variant_id', flat=True))

    return render(request, "products/products_list.html", {
        "product_data": page_obj,
        'page_obj': page_obj,
        "subcategories": subcategories,
        "total_count": total_count,
        "query_string": query_string,
        "sub_query_string": sub_query_string,
        "selected_categories": subcategory,
        "current_sort": sort,
        "wishlist_variant_ids": wishlist_variant_ids,
    })
    
def product_details(request,slug):

    product = get_object_or_404(Products, slug=slug, is_deleted=False,is_active=True)
    reviews = product.reviews.all()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    if product.is_active == False or product.subcategory.is_active == False or product.category.is_active == False:
        return redirect('product_list')
    
    variants = product.variants.filter(is_deleted=False)
    similar_products = Products.objects.filter(subcategory__name=product.subcategory.name,is_deleted=False,is_active=True).exclude(id=product.id)[:8]
    change_variant = request.GET.get('variant')
    is_in_cart = False
    user_cart_variants = []
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            if change_variant:
                is_in_cart = CartItem.objects.filter(cart=cart, variant_id=change_variant).exists()
            user_cart_variants = list(CartItem.objects.filter(cart=cart).values_list('variant_id', flat=True))
        except Cart.DoesNotExist:
            pass
            
    if change_variant:
        default_variant = variants.filter(id=change_variant,is_deleted=False).first()
    else:
        default_variant = variants.filter(is_default=True).first()

    if not default_variant:
        default_variant = variants.first()
    base_price = default_variant.price
    final_price, discount, discount_percent = get_best_offer(product, base_price)
        
    color_variants = variants.filter(color=default_variant.color,is_deleted=False)
    
    
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

    is_in_wishlist = False
    if request.user.is_authenticated and default_variant:
        is_in_wishlist = Wishlist.objects.filter(user=request.user, variant=default_variant).exists()

    # ── Reviews ────────────────────────────────────────────────────────────
    all_reviews  = product.reviews.select_related('user').prefetch_related('images')
    total_reviews = all_reviews.count()
    avg_rating    = all_reviews.aggregate(avg=Avg('rating'))['avg']
    avg_rating    = round(avg_rating, 1) if avg_rating else None

    REVIEWS_PER_PAGE = 6
    reviews      = all_reviews[:REVIEWS_PER_PAGE]
    has_more_reviews = total_reviews > REVIEWS_PER_PAGE

    # Star breakdown (5 down to 1)
    rating_breakdown = []
    for star in range(5, 0, -1):
        cnt = all_reviews.filter(rating=star).count()
        pct = round((cnt / total_reviews) * 100) if total_reviews else 0
        rating_breakdown.append({'stars': star, 'count': cnt, 'percent': pct})

    # Items the logged-in user can review (DELIVERED, not yet reviewed)
    reviewable_items = []
    if request.user.is_authenticated:
        reviewed_item_ids = set(
            Review.objects.filter(user=request.user, product=product)
            .values_list('order_item_id', flat=True)
        )
        reviewable_items = list(
            OrderItem.objects.filter(
                order__user=request.user,
                variant__product=product,
                status='DELIVERED',
            ).exclude(id__in=reviewed_item_ids)
            .select_related('variant')
        )

    return render(request, "products/product_details.html", {
        "product": product,
        "default_variant": default_variant,
        "sizes": sizes,
        "colors": colors,
        "color_variants": color_variants,
        "is_in_cart": is_in_cart,
        "change_variant": change_variant,
        "similar_products": similar_products,
        "is_in_wishlist": is_in_wishlist,
        "final_price": final_price,
        "discount": discount,
        "discount_percent": discount_percent,
        # reviews
        "reviews": reviews,
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "rating_breakdown": rating_breakdown,
        "has_more_reviews": has_more_reviews,
        "reviewable_items": reviewable_items,
        "user_cart_variants": user_cart_variants,
    })
    
    
def add_to_cart(request,slug):
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        variant_id = request.POST.get('variant_id')
            
        if not variant_id:
            if is_ajax:
                return JsonResponse({"success": False, "message": "choose a size"})
            messages.error(request,"choose a size ")
            return redirect(f'/products/{slug}')
        
        variant = get_object_or_404(Variants,id=variant_id)
        
        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({"success": False, "redirect": "/login/"})
            return redirect('/login/')
            
        cart,_= Cart.objects.get_or_create(user=request.user)
        item,created = CartItem.objects.get_or_create(cart=cart,variant=variant)
        cart_count = CartItem.objects.filter(cart=cart).count()
        
        toast_data = {
            "product": variant.product.name,
            "price": float(variant.price),
            "size": variant.size,
            "color": variant.color,
            "image": variant.images.first().image.url if variant.images.exists() else ""
        }
        
        if is_ajax:
            return JsonResponse({
                "success": True, 
                "cart_count": cart_count,
                "toast_data": toast_data
            })
            
        messages.success(request, "added") 
        request.session['toast_data'] = toast_data
        return redirect(f'/products/{slug}?variant={variant_id}')
        


def clear_toast(request):
    request.session.pop('toast_data', None)
    return HttpResponse('hello world')

    

    