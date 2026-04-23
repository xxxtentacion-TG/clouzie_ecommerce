from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from adminpanel.models import Variants,Products,VariantImage
from decimal import Decimal
from decimal import Decimal
from django.core.files.base import ContentFile
from django.core.paginator import Paginator

@login_required(login_url="adminpanel:admin-login")
def product_variants(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    product = get_object_or_404(Products,id=id)
    variants_list = Variants.objects.filter(product_id=id).order_by('id').exclude(is_deleted=True)
    paginator = Paginator(variants_list,5) 
    page_number = request.GET.get('page')
    variants = paginator.get_page(page_number)
    
    return render(request,"adminpanel/variants/variants.html",{
        "product":product,
        "variants":variants,
        "sizes":Variants.SIZE_CHOICES,
        'colors':Variants.COLOR_CHOICES
        })

@login_required(login_url="adminpanel:admin-login")
def add_variant(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    if request.method == "POST":
        product_id = request.POST.get('product_id')
        size = request.POST.get('size').strip()
        color = request.POST.get('color').strip()
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        images = []
        for i in range(3):
            img = request.FILES.get(f'image_{i}')
            if img:
                images.append(img)
                
        is_active = request.POST.get('is_active') == 'on'
        products = get_object_or_404(Products,id=product_id)
        new_price = Decimal(price) if price else None
        if not size:
            messages.error(request,"size is required")
            return redirect('adminpanel:product-variants',id=product_id)
        
        if not color:
            messages.error(request,"Color is required")
            return redirect('adminpanel:product-variants',id=product_id)
        
        if not price:
            messages.error(request,"Price is required")
            return redirect('adminpanel:product-variants',id=product_id)
        
        if not stock:
            messages.error(request,"stock is required")
            return redirect('adminpanel:product-variants',id=product_id)
        
        if len(images) == 0 or len(images) > 3:
            messages.error(request,"1 to 3 images needed")
            return redirect('adminpanel:product-variants',id=product_id)
        
        try:
            price = Decimal(price) if price else None
            if price <=0:
                messages.error(request,"Price must > 0")
                return redirect('adminpanel:product-variants',id=product_id)
            
        except:
            messages.error(request,"someting went wrong..")
            return redirect('adminpanel:product-variants',id=product_id)
        
        try:
            stock = int(stock)
            if stock < 0:
                messages.error(request,"stock must be > 0")
                return redirect('adminpanel:product-variants',id=product_id)
            
        except:
            messages.error(request,"someting went wrong..")
            return redirect('adminpanel:product-variants',id=product_id)
        
        exists = Variants.objects.filter(
            product=products,
            size__iexact=size,
            color__iexact=color
        ).exists()

        if exists:
            messages.error(request,"Variant already exists")
            return redirect('adminpanel:product-variants',id=product_id)
        variants = Variants.objects.create(
            product = products,
            size = size,
            color = color,
            price = new_price,
            is_active = is_active,
            stock = stock
        )
        
        for index, img in enumerate(images):
            VariantImage.objects.create(
                image=img,
                variant=variants,
                position=index
            )
        messages.success(request,"Variant added successfully.")
        return redirect('adminpanel:product-variants',id=product_id)
    return redirect('adminapanel:add_variant')


@login_required(login_url="adminpanel:admin-login")
def update_variants(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    variant = get_object_or_404(Variants,id=id)
    if request.method == "POST":
        product_id = request.POST.get('product_id')
        size = request.POST.get('size')
        color = request.POST.get('color')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        is_active = request.POST.get('is_active') == 'on'
        valid_count = 0
        for i in range(3):
            if request.FILES.get(f'image_{i}') or request.POST.get(f'existing_image_url_{i}'):
                valid_count += 1
                
        if valid_count == 0 or valid_count < 3:
            messages.error(request, "1 to 3 images needed")
            return redirect('adminpanel:product-variants',id=product_id)

        if not size or not color:
            messages.error(request,"size and Color required")
            return redirect('adminpanel:product-variants',id=product_id)
        
        
        try:
            price = Decimal(price)
            stock = int(stock)
            if stock < 0:
                messages.error(request,"stock must be > 0")
                return redirect('adminpanel:product-variants',id=product_id)
            if price <=0:
                messages.error(request,"Price must > 0")
                return redirect('adminpanel:product-variants',id=product_id)
            
        except:
            messages.error(request,"invalid stock or price")
            return redirect('adminpanel:product-variants',id=product_id)
        exists = Variants.objects.filter(
            product=variant.product,
            size__iexact=size,
            color__iexact=color
            ).exclude(id=variant.id).exists()
        
        if exists:
            messages.error(request,"Variant already exists")
            return redirect('adminpanel:product-variants',id=product_id)
        variant.size = size
        variant.color = color
        variant.price = price
        variant.stock = stock
        variant.is_active = is_active
        variant.save()
        existing_models = list(variant.images.all().order_by('id'))
        
        for i in range(3):
            new_file = request.FILES.get(f'image_{i}')
            kept_url = request.POST.get(f'existing_image_url_{i}')
            if new_file:
                if i < len(existing_models):
                    existing_models[i].image = new_file
                    existing_models[i].position = i
                    existing_models[i].save()
                else:
                    VariantImage.objects.create(variant=variant, image=new_file, position=i)
            elif kept_url:
                if i < len(existing_models):
                    existing_models[i].position = i
                    existing_models[i].save()
            else:
                if i < len(existing_models):
                    existing_models[i].delete()
 
        messages.success(request,"Variant updated succesfully.")
        return redirect('adminpanel:product-variants',id=product_id)


@login_required(login_url="adminpanel:admin-login")  
def delete_variants(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    variant = get_object_or_404(Variants,id=id)
    product_id = variant.product.id
    variant.is_deleted  = True
    variant.save()
    return redirect('adminpanel:product-variants',id=product_id)


def toggle_variant(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    if request.method == "POST":
        variant = get_object_or_404(Variants,id=id)
        product_id = variant.product.id
        is_active = request.POST.get('is_active') == 'on'
        variant.is_active = is_active
        variant.save()
        return redirect('adminpanel:product-variants',id=product_id)
    
def set_default_variant(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    if request.method == "POST":
        variant = get_object_or_404(Variants,id=id)
        product_id = variant.product.id
        default_variant = request.POST.get('default_variant') == 'on'
        variant.is_default = default_variant
        Variants.objects.filter(product__id=product_id).update(is_default=False)
        variant.save()
        return redirect('adminpanel:product-variants',id=product_id)
    
    
        
    
    

        