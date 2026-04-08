from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from adminpanel.models import Category,Subcategory
def categories(request):
    categories = Category.objects.filter(is_deleted=False).values('id','name','is_active')
    return render(request,"adminpanel/category/category.html",{"categories":categories})

def add_categories(request):
    if request.method == "POST":
        category_name = request.POST.get('name')
        toggle = request.POST.get('is_active') == "on"
        
        if not category_name:
            messages.error(request,"This field cannot be empty.")
            return redirect('adminpanel:add_category')
        
        
        if len(category_name) <=2:
            messages.error(request,"Category name is too short.")
            return redirect('adminpanel:add_category')
        
        if Category.objects.filter(name__iexact=category_name).exists():
            messages.error(request,"category already existing now")
            return redirect('adminpanel:add_category')
        Category.objects.create(
            name=category_name,
            is_active=toggle,
        )
        messages.success(request,'Category added successfully')
        return redirect('adminpanel:category')
    return render(request,"adminpanel/category/add_category.html")

def edit_categories(request,id):
    category = get_object_or_404(Category,id=id)
    if request.method == "POST":
        name = request.POST.get("name")
        is_active = request.POST.get('is_active') == 'on'
        
        if category.name == name and category.is_active == is_active:
            messages.error(request,"No changes detected")
            return redirect('adminpanel:edit_category',id=id)

        if len(name) <=2:
            messages.error(request,"Category name is too short.")
            return redirect('adminpanel:edit_category',id=id)
            
        if name != category.name:
            
            if Category.objects.filter(name__iexact=name).exists():
                messages.error(request,"category already existing now")
                return redirect('adminpanel:edit_category',id=id)
        if not name:
            messages.error(request,"This field cannot be empty.")
            return redirect('adminpanel:edit_category',id=id)
        
        category.is_active = is_active
        category.name = name
        category.save()
        messages.success(request,"Category added successfully")
        return redirect('adminpanel:category')
    return render(request,"adminpanel/category/edit_category.html",{"category":category})

def toggle_status(request,id):
    
    if request.method == "POST":
        category = get_object_or_404(Category,id=id)
        toggle = request.POST.get('toggle') == 'on'
        print(toggle)
        category.is_active = toggle
        category.save()
        return redirect('adminpanel:category')
    return redirect('adminpanel:category') 

def delete_category(request,id):
    if request.method == "POST":
        
        category = get_object_or_404(Category,id=id)
        category.is_deleted = True
        print("DB hit ")
        category.save()
        return redirect('adminpanel:category')
    return redirect('adminpanel:category')

def subcategory(request):
    subcategories = Subcategory.objects.all()
    return render(request,"adminpanel/subcategory/subcategory.html",{"subcategories":subcategories})

def add_subcategory(request):
    categories = Category.objects.filter(is_active=True,is_deleted=False)
    
    if request.method == 'POST':
        subcategory = request.POST.get('subcategory')
        category_id = request.POST.get('category')
        is_active = request.POST.get('is_active') == 'on'
        exist = Subcategory.objects.filter(
            name__iexact=subcategory,
            category=category_id,
            is_deleted=False,
            )
        if exist:
            messages.error(request,"A subcategory with this name already exists under the selected category.")
            return redirect('adminpanel:add_subcategory')
        
        if not subcategory and not category_id:
            messages.error(request,"This field cannot be empty.")
            return redirect('adminpanel:add_subcategory')
        if len(subcategory) <=2:
            messages.error(request,"Subcategory name is too short.")
            return redirect('adminpanel:add_category')
        
        category = get_object_or_404(Category,id=category_id)
        Subcategory.objects.create(
            name=subcategory,
            category=category,
            is_active=is_active,
        )
        messages.success(request,"Subcategory added successfully")
        return redirect('adminpanel:subcategory')
        
    return render(request,"adminpanel/subcategory/add_subcategory.html",{"categories":categories})

def edit_subcategory(request,id):
    subcategory = get_object_or_404(Subcategory,id=id)
    categories = Category.objects.all()
    if request.method == "POST":
        name = request.POST.get('name')
        category = request.POST.get('category')
        is_active = request.POST.get('is_active') == 'on'
        cat = Category.objects.get(id=subcategory.category.id)
        
        if ( 
            subcategory.name == name and
            subcategory.category.id == int(category) and
            subcategory.is_active == is_active
        ):
            messages.error(request,"No changes detected")
            return redirect('adminpanel:edit_subcategory',id=id)
        
        
        if not name or not category:
            messages.error(request,"This field cannot be empty.")
            return redirect('adminpanel:edit_subcategory',id=id)
        
        if len(name) >=1 and len(name) <=2:
            messages.error(request,'Subcategory name is too short.')
            return redirect('adminpanel:edit_subcategory',id=id)
        
        
        
        
        subcategory.name = name
        subcategory.category = cat
        subcategory.save()
        messages.success(request,"updated successfully")
        return redirect('adminpanel:subcategory')
    
    return render(request,"adminpanel/subcategory/edit_subcategory.html",{"subcategory":subcategory,"categories":categories})