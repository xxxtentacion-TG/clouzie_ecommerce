from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from adminpanel.models import Category,Subcategory,Products
from django.utils.text import slugify
from decimal import Decimal,InvalidOperation
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from adminpanel.models import Variants
from adminpanel.utils.admin_gaurd import admin_required
import re
@admin_required
def products(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    query = request.GET.get('q', '').strip()
    products_list = Products.objects.filter(is_deleted=False).prefetch_related(
        Prefetch('variants', queryset=Variants.objects.filter(is_deleted=False), to_attr='active_variants')
    ).order_by('-created_at')
    if query:
        products_list = products_list.filter(
            Q(name__icontains=query)
        )
        
    paginator = Paginator(products_list,5)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    return render(request,"adminpanel/products/products.html",{"products":products})

@admin_required
def add_products(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    categories = Category.objects.exclude(is_deleted=True).values('id','name')
    subcategories = Subcategory.objects.exclude(is_deleted=True).values('id','name')
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        weight = request.POST.get('weight', '').strip()
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory')
        description = request.POST.get('description', '').strip()
        materials = request.POST.get('materials', '').strip()
        care_guide = request.POST.get('care_guide', '').strip()
        delivery = request.POST.get('delivery', '').strip()
        payment_returns = request.POST.get('payment_returns', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if (
            not name or 
            not weight or
            not category_id or 
            not subcategory_id or 
            not description or 
            not materials or 
            not care_guide or 
            not delivery or 
            not payment_returns
        ):
            messages.error(request,"This field cannot be empty.")
            return redirect('adminpanel:add_products')
        if len(name) < 3:
            messages.error(request, "Product name must be at least 3 characters.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })

        if not re.match(r'^[A-Za-z0-9\s\-&]+$', name):
            messages.error(request, "Product name can only contain letters, numbers, spaces, hyphen and &.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })

        try:
            weight = Decimal(weight)
            if weight <= 0:
                messages.error(request, "Weight must be greater than 0.")
                return render(request, "adminpanel/products/add_products.html", {
                "categories": categories,
                "subcategories": subcategories,
                "form_data": request.POST
            })
        except:
            messages.error(request, "Enter a valid weight.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })

        if len(description) < 10:
            messages.error(request, "Description must be at least 10 characters.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })

        if len(materials) < 3:
            messages.error(request, "Materials must be at least 3 characters.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })

        if len(care_guide) < 5:
            messages.error(request, "Care guide must be at least 5 characters.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })

        if len(delivery) < 5:
            messages.error(request, "Delivery information must be at least 5 characters.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })

        if len(payment_returns) < 5:
            messages.error(request, "Payment and returns information must be at least 5 characters.")
            return render(request, "adminpanel/products/add_products.html", {
            "categories": categories,
            "subcategories": subcategories,
            "form_data": request.POST
        })
        
        if not slug:
            slug = slugify(name)
            
        if Products.objects.filter(slug=slug).exists():
            messages.error(request,"Slug already exists")
            return redirect('adminpanel:add_products')
    
          
        product = Products.objects.create(
            name=name,
            slug=slug,
            weight=weight,
            category_id=category_id,
            subcategory_id=subcategory_id,
            description=description,
            materials=materials,
            care_guide=care_guide,
            delivery =delivery,
            payment_returns=payment_returns,
            is_active=is_active,
        )
        messages.success(request,"Product added successfully.")
        return redirect('adminpanel:product-variants', uuid=product.uuid)
        
        
    return render(request,"adminpanel/products/add_products.html",{"categories":categories,"subcategories":subcategories})


@admin_required
def edit_products(request, uuid):
    categories = Category.objects.exclude(is_deleted=True).values('id', 'name')
    subcategories = Subcategory.objects.exclude(is_deleted=True).values('id', 'name')
    product = get_object_or_404(Products, uuid=uuid)

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        weight = request.POST.get('weight', '').strip()
        category = request.POST.get('category')
        subcategory = request.POST.get('subcategory')
        description = request.POST.get('description', '').strip()
        materials = request.POST.get('materials', '').strip()
        care_guide = request.POST.get('care_guide', '').strip()
        delivery = request.POST.get('delivery', '').strip()
        payment_returns = request.POST.get('payment_returns', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        context = {
            "categories": categories,
            "subcategories": subcategories,
            "product": product,
            "form_data": request.POST,
        }

        if (
            not name or not weight or not category or not subcategory or
            not description or not materials or not care_guide or
            not delivery or not payment_returns
        ):
            messages.error(request, "This field cannot be empty.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if len(name) < 3:
            messages.error(request, "Product name must be at least 3 characters.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if not re.match(r'^[A-Za-z0-9\s\-&]+$', name):
            messages.error(request, "Product name can only contain letters, numbers, spaces, hyphen and &.")
            return render(request, "adminpanel/products/edit_products.html", context)

        try:
            weight_val = Decimal(weight)
            if weight_val <= 0:
                messages.error(request, "Weight must be greater than 0.")
                return render(request, "adminpanel/products/edit_products.html", context)
        except:
            messages.error(request, "Enter a valid weight.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if len(description) < 10:
            messages.error(request, "Description must be at least 10 characters.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if len(materials) < 3:
            messages.error(request, "Materials must be at least 3 characters.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if len(care_guide) < 5:
            messages.error(request, "Care guide must be at least 5 characters.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if len(delivery) < 5:
            messages.error(request, "Delivery information must be at least 5 characters.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if len(payment_returns) < 5:
            messages.error(request, "Payment and returns information must be at least 5 characters.")
            return render(request, "adminpanel/products/edit_products.html", context)

        if not slug:
            slug = slugify(name)

        if Products.objects.exclude(id=product.id).filter(slug=slug).exists():
            messages.error(request, "Slug is already existing.")
            return render(request, "adminpanel/products/edit_products.html", context)

        cat = Category.objects.get(id=category)
        sub = Subcategory.objects.get(id=subcategory)

        if (
            product.name == name and
            product.slug == slug and
            product.weight == weight_val and
            product.category == cat and
            product.subcategory == sub and
            product.description == description and
            product.materials == materials and
            product.care_guide == care_guide and
            product.delivery == delivery and
            product.payment_returns == payment_returns and
            product.is_active == is_active
        ):
            messages.error(request, "No changes detected.")
            return render(request, "adminpanel/products/edit_products.html", context)

        product.name = name
        product.slug = slug
        product.weight = weight_val
        product.category = cat
        product.subcategory = sub
        product.description = description
        product.materials = materials
        product.care_guide = care_guide
        product.delivery = delivery
        product.payment_returns = payment_returns
        product.is_active = is_active
        product.save()

        messages.success(request, "Product updated successfully.")
        return redirect('adminpanel:products')

    return render(request, "adminpanel/products/edit_products.html", {
        "categories": categories,
        "subcategories": subcategories,
        "product": product
    })
    
@admin_required
def delete_products(request,uuid):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    product = get_object_or_404(Products,uuid=uuid)
    if request.method == "POST":
        product.is_deleted = True
        product.save()
        return redirect('adminpanel:products')
    return redirect('adminpanel:products')

@admin_required
def view_product(request,uuid):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    product = Products.objects.get(uuid=uuid)
    
    return render(request,"adminpanel/products/view_products.html",{'product':product})
