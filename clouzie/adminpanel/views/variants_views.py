from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from adminpanel.models import Variants,Products,VariantImage
from decimal import Decimal
from decimal import Decimal
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from adminpanel.utils.admin_gaurd import admin_required
from django.urls import reverse

@admin_required
def product_variants(request,uuid):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    product = get_object_or_404(Products,uuid=uuid)
    variants_list = Variants.objects.filter(product__uuid=uuid).order_by('id').exclude(is_deleted=True)
    paginator = Paginator(variants_list,5) 
    page_number = request.GET.get('page')
    variants = paginator.get_page(page_number)
    
    open_edit_modal_id = request.GET.get("open_edit_modal")
    edit_variant_obj = None
    if open_edit_modal_id:
        edit_variant_obj = Variants.objects.filter(id=open_edit_modal_id).first()

    return render(request,"adminpanel/variants/variants.html",{
        "product":product,
        "variants":variants,
        "variant_form_data": request.GET,
        "open_variant_modal": request.GET.get("open_modal") == "1",
        "open_edit_modal_id": open_edit_modal_id,
        "edit_variant_obj": edit_variant_obj,
        "sizes":Variants.SIZE_CHOICES,
        'colors':Variants.COLOR_CHOICES
        })

@admin_required
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
        
        def variant_error(message):
            messages.error(request, message)
            return redirect(f"{reverse('adminpanel:product-variants', kwargs={'uuid': products.uuid})}?open_modal=1&size={size}&color={color}&price={price}&stock={stock}&is_active={is_active}")
        
        new_price = Decimal(price) if price else None
        if not size:
            return variant_error("Size is required")
        
        if not color:
            return variant_error("Color is required")
        
        if not price:
            return variant_error("Price is required")
        
        if not stock:
            return variant_error("Stock is required")
        
        if len(images) == 0 or len(images) > 3:
            return variant_error("Please upload 1 to 3 images")
        
        try:
            price = Decimal(price) if price else None
            if price <= 0:
                return variant_error("Price must be greater than 0")
        except Exception:
            return variant_error("Enter a valid price")
        
        try:
            stock = int(stock)
            if stock < 0:
                return variant_error("Stock must be 0 or greater")
        except Exception:
            return variant_error("Enter a valid stock quantity")
        
        exists = Variants.objects.filter(
            product=products,
            size__iexact=size,
            color__iexact=color
        ).exists()

        if exists:
            return variant_error("A variant with this size and color already exists")
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
        messages.success(request,"Variant added successfully.", extra_tags="toast")
        return redirect('adminpanel:product-variants',uuid=products.uuid)
    return redirect('adminpanel:products')


@admin_required
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

        def edit_error(message):
            messages.error(request, message, extra_tags="toast")
            return redirect(
                f"{reverse('adminpanel:product-variants', kwargs={'uuid': variant.product.uuid})}"
                f"?open_edit_modal={variant.id}&edit_size={size}&edit_color={color}&edit_price={price}&edit_stock={stock}&edit_is_active={is_active}"
            )

        valid_count = 0
        for i in range(3):
            if request.FILES.get(f'image_{i}') or request.POST.get(f'existing_image_url_{i}'):
                valid_count += 1

        if valid_count == 0 or valid_count < 3:
            return edit_error("Please ensure all 3 image slots are filled")

        if not size or not color:
            return edit_error("Size and Color are required")

        try:
            price = Decimal(price)
            stock = int(stock)
            if stock < 0:
                return edit_error("Stock must be 0 or greater")
            if price <= 0:
                return edit_error("Price must be greater than 0")
        except Exception:
            return edit_error("Enter a valid price and stock quantity")

        exists = Variants.objects.filter(
            product=variant.product,
            size__iexact=size,
            color__iexact=color
            ).exclude(id=variant.id).exists()

        if exists:
            return edit_error("A variant with this size and color already exists")
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
 
        messages.success(request,"Variant updated succesfully.", extra_tags="toast")
        return redirect('adminpanel:product-variants', uuid=variant.product.uuid)


@admin_required  
def delete_variants(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    variant = get_object_or_404(Variants,id=id)
    product_id = variant.product.id
    variant.is_deleted  = True
    variant.save()
    messages.success(request, "Variant deleted successfully.", extra_tags="toast")
    return redirect('adminpanel:product-variants', uuid=variant.product.uuid)

@admin_required
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
        return redirect('adminpanel:product-variants', uuid=variant.product.uuid)

@admin_required   
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
        return redirect('adminpanel:product-variants', uuid=variant.product.uuid)
    
    
        
    
    

        