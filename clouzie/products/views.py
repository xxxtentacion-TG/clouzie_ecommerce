from django.shortcuts import render
from adminpanel.models import Products
# Create your views here.
def products_list(request):

    products = Products.objects.filter(is_deleted=False,is_active=True).prefetch_related("variants__images")

    product_data = []

    for product in products:
        variant = product.variants.filter(is_default=True).first()

        if not variant:
            variant = product.variants.first()

        product_data.append({
            "product": product,
            "variant": variant
        })
    return render(request, "products/products_list.html", {
        "product_data": product_data
    })
    