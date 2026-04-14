from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from adminpanel.models import Category,Subcategory,Products
from django.utils.text import slugify
from decimal import Decimal,InvalidOperation
from django.core.paginator import Paginator
def products(request):
    
    products_list = Products.objects.filter(is_deleted=False)
    paginator = Paginator(products_list,5)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    return render(request,"adminpanel/products/products.html",{"products":products})

def add_products(request):
    categories = Category.objects.exclude(is_deleted=True).values('id','name')
    subcategories = Subcategory.objects.exclude(is_deleted=True).values('id','name')
    if request.method == "POST":
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        weight = request.POST.get('weight')
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory')
        description = request.POST.get('description')
        materials = request.POST.get('materials')
        care_guide = request.POST.get('care_guide')
        delivery  = request.POST.get('delivery')
        payment_returns = request.POST.get('payment_returns')
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
        
        if description and len(description) <= 10:
            messages.error(request,"Description is too short.")
            return redirect('adminpanel:add_products')
        if not slug:
            slug = slugify(name)
            
        if Products.objects.filter(slug=slug).exists():
            messages.error(request,"Slug already exists")
            return redirect('adminpanel:add_products')
        
        weight = Decimal(weight) if weight else None
          
        Products.objects.create(
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
        return redirect('adminpanel:products')
        
        
    return render(request,"adminpanel/products/add_products.html",{"categories":categories,"subcategories":subcategories})

def edit_products(request,id):
    categories = Category.objects.exclude(is_deleted=True).values('id','name')
    subcategories = Subcategory.objects.exclude(is_deleted=True).values('id','name')
    products = get_object_or_404(Products,id=id)
    
    if request.method =="POST":
        product = get_object_or_404(Products,id=id)
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        weight = request.POST.get('weight')
        category = request.POST.get('category')
        subcategory = request.POST.get('subcategory')
        description = request.POST.get('description')
        materials = request.POST.get('materials')
        care_guide = request.POST.get('care_guide')
        delivery = request.POST.get('delivery')
        payment_returns = request.POST.get('payment_returns')
        is_active = request.POST.get('is_active') == 'on'
        cat = Category.objects.get(id=category)
        sub = Subcategory.objects.get(id=subcategory)
        weight_val = Decimal(weight) if weight else None
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
            
            messages.error(request,"No changes detected")
            return redirect('adminpanel:edit_products',id=id)
        
        if (
            not name or 
            not weight or
            not category or 
            not subcategory or 
            not description or 
            not materials or 
            not care_guide or 
            not delivery or 
            not payment_returns
        ):
            messages.error(request,"This field cannot be empty.")
            return redirect('adminpanel:edit_products',id=id)

        if weight:
            try:
                weight = Decimal(weight)
                if weight <= 0:
                    messages.error(request,"Weight must be greater than 0")
                    return redirect('adminpanel:edit_products',id=id)
                
            except InvalidOperation:
                messages.error(request,"Invalid weight format")
                return redirect('adminpanel:edit_products',id=id)
                    
        if Products.objects.exclude(id=product.id).filter(slug=slug).exists():
            messages.error(request,"Slug is already existing")
            return redirect('adminpanel:edit_products',id=id)
        
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
        messages.success(request,"Product upated succesfully")
        return redirect('adminpanel:products')
    
        
        
    return render(request,"adminpanel/products/edit_products.html", {"categories":categories,
                   "subcategories":subcategories,
                   "product":products})
    
    
def delete_products(request,id):
    product = get_object_or_404(Products,id=id)
    if request.method == "POST":
        product.is_deleted = True
        product.save()
        return redirect('adminpanel:products')
    return redirect('adminpanel:products')

def view_product(request,id):
    product = Products.objects.get(id=id)
    
    return render(request,"adminpanel/products/view_products.html",{'product'})
