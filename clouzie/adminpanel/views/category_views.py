from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from adminpanel.models import Category,Subcategory
@login_required(login_url="adminpanel:admin-login")
def categories(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    categories = Category.objects.filter(is_deleted=False)
    return render(request,"adminpanel/category/category.html",{"categories":categories})

@login_required(login_url="adminpanel:admin-login")
def add_categories(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
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

@login_required(login_url="adminpanel:admin-login")
def edit_categories(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
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
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    if request.method == "POST":
        category = get_object_or_404(Category,id=id)
        toggle = request.POST.get('toggle') == 'on'
        category.is_active = toggle
        category.save()
        return redirect('adminpanel:category')
    return redirect('adminpanel:category') 

@login_required(login_url="adminpanel:admin-login")
def delete_category(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    if request.method == "POST":
        
        category = get_object_or_404(Category,id=id)
        category.is_deleted = True
        print("DB hit ")
        category.save()
        return redirect('adminpanel:category')
    return redirect('adminpanel:category')

@login_required(login_url="adminpanel:admin-login")
def subcategory(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    subcategories = Subcategory.objects.exclude(is_deleted=True)
    search = request.GET.get('q')
    total_count = subcategories.count()
    active_count = subcategories.filter(is_active=True).count()
    inactive_count = subcategories.filter(is_active=False).count()
    categories = Category.objects.values('name','id')
    items = {
        'total_count':total_count,
        'inactive_count':inactive_count,
        'active_count':active_count,
    }
    if search:
        subcategories = Subcategory.objects.filter(name__icontains=search)
        
    return render(request,"adminpanel/subcategory/subcategory.html",{"subcategories":subcategories,"items":items,'categories':categories})


@login_required(login_url="adminpanel:admin-login")
def add_subcategory(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    categories = Category.objects.filter(is_active=True,is_deleted=False)
    
    if request.method == 'POST':
        subcategory = request.POST.get('subcategory','').strip()
        category_id = request.POST.get('category')
        is_active = request.POST.get('is_active') == 'on'
        
        if not subcategory or not category_id:
            messages.error(request,"This field cannot be empty.")
            return redirect('adminpanel:add_subcategory')
            
        exist = Subcategory.objects.filter(
            name__iexact=subcategory,
            category=category_id,
            is_deleted=False,
            )
        if exist:
            messages.error(request,"A subcategory with this name already exists under the selected category.")
            return redirect('adminpanel:add_subcategory')
        
        if len(subcategory) <=2:
            messages.error(request,"Subcategory name is too short.")
            return redirect('adminpanel:add_subcategory')
        
        category = get_object_or_404(Category,id=category_id)
        Subcategory.objects.create(
            name=subcategory,
            category=category,
            is_active=is_active,
        )
        messages.success(request,"Subcategory added successfully")
        return redirect('adminpanel:subcategory')
        
    return render(request,"adminpanel/subcategory/add_subcategory.html",{"categories":categories})

@login_required(login_url="adminpanel:admin-login")
def edit_subcategory(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    subcategory = get_object_or_404(Subcategory,id=id)
    categories = Category.objects.all()
    if request.method == "POST":
        name = request.POST.get('name','').strip()
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
        
        if category:
            
            exist = Subcategory.objects.filter(
                name__iexact=name,
                category=subcategory.category.id,
                is_deleted=False,
                )
        
        if exist:
            messages.error(request,"A subcategory with this name already exists under the selected category.")
            return redirect('adminpanel:edit_subcategory',id=id)
        
        if len(name) >=1 and len(name) <=2:
            messages.error(request,'Subcategory name is too short.')
            return redirect('adminpanel:edit_subcategory',id=id)
        
        
        subcategory.name = name
        subcategory.category = cat
        subcategory.is_active = is_active
        subcategory.save()
        messages.success(request,"updated successfully")
        return redirect('adminpanel:subcategory')
    
    return render(request,"adminpanel/subcategory/edit_subcategory.html",{"subcategory":subcategory,"categories":categories})

@login_required(login_url="adminpanel:admin-login")
def delete_subcategory(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    subcategory = get_object_or_404(Subcategory,id=id)
    if request.method == "POST": 
        subcategory.is_deleted = True
        subcategory.save()
    return redirect('adminpanel:subcategory')


def toggle_subcategory(request,id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    if request.method == "POST":
        subcategory = get_object_or_404(Subcategory,id=id)
        toggle = request.POST.get('toggle') == 'on'
        subcategory.is_active = toggle
        subcategory.save()
        return redirect('adminpanel:subcategory')
    return redirect('adminpanel:subcategory')
    