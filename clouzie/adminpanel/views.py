from django.shortcuts import render,redirect
from django.http import HttpResponse
from accounts.models import CustomUser,Address
from django.contrib.auth import authenticate
from django.contrib.auth import login,logout
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
def admin_login(request):
    if request.user.is_authenticated:
        return redirect('adminpanel:admin-dashboard')
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(email)
        print(password)
        
        try: 
            user_obj = CustomUser.objects.get(email=email)
        
            user = authenticate(request,email=user_obj.email,password=password)
            
            if user is not None and user_obj.is_admin_user:
                login(request,user)
                request.session['user_id'] = user.id
                request.session.set_expiry(1209600)
                print(request.user)
                return redirect('adminpanel:admin-dashboard')
            return render(request,"adminpanel/login.html",{"error":"invalid email or password"})
        
        except CustomUser.DoesNotExist:
            return render(request,"adminpanel/login.html",{"error":"invalid email or password"})
    return render(request,'adminpanel/login.html')

@login_required(login_url="adminpanel:admin-login")      
def admin_dashboard(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
    return render(request,'adminpanel/dashboard.html')


@login_required(login_url="adminpanel:admin-login")  
def customers(request):
    query = request.GET.get('q','').strip()
    user_list = CustomUser.objects.all().order_by('-created_at').exclude(is_admin_user=True)
    paginator = Paginator(user_list,5)
    page_number = request.GET.get('page')
    
    if query:
        users = CustomUser.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )
    else:
        
        users = paginator.get_page(page_number)
    status = request.GET.get('status')
    if status == 'Active':
        users = CustomUser.objects.filter(is_blocked=False)
    
    elif status == 'inactive':
        users = CustomUser.objects.filter(is_blocked=True)
            
    return render(request,"adminpanel/customers.html",{"users":users})

@login_required(login_url="adminpanel:admin-login")  
def customers_details(request,id):
    User_obj = CustomUser.objects.get(id=id)
    address = Address.objects.filter(user_id=User_obj.id,is_default=True).first()
    return render(request,"adminpanel/user_details.html",{'user_obj':User_obj,"address":address})

@login_required(login_url="adminpanel:admin-login")  
def customer_block(request,id):
    user = CustomUser.objects.get(id=id)
    user.is_blocked = True
    user.save()
    return redirect('adminpanel:customers')

@login_required(login_url="adminpanle:admin-login")  
def customer_unblock(request,id):
    user = CustomUser.objects.get(id=id)
    user.is_blocked = False
    user.save()
    return redirect('adminpanel:customers')
  
def logout_admin(request):
    logout(request)
    return redirect('adminpanel:admin-login')
    