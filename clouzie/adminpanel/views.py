from django.shortcuts import render,redirect
from django.http import HttpResponse
from accounts.models import CustomUser,Address
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.core.paginator import Paginator


def admin_login(request):
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
                return redirect('admin-dashboard')
            return render(request,"adminpanel/login.html",{"error":"invalid email or password"})
        
        except CustomUser.DoesNotExist:
            return render(request,"adminpanel/login.html",{"error":"invalid email or password"})
    return render(request,'adminpanel/login.html')
        
def admin_dashboard(request):
    return render(request,'adminpanel/dashboard.html')

def customers(request):
    user_list = CustomUser.objects.all().order_by('-created_at')
    paginator = Paginator(user_list,5)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    return render(request,"adminpanel/customers.html",{"users":users})

def customers_details(request,id):
    User_obj = CustomUser.objects.get(id=id)
    address = Address.objects.filter(user_id=User_obj.id,is_default=True).first()
    return render(request,"adminpanel/user_details.html",{'user_obj':User_obj,"address":address})

def customer_block(request,id):
    user = CustomUser.objects.get(id=id)
    user.is_blocked = True
    user.save()
    return redirect('customers_details',id=user.id)
def customer_unblock(request,id):
    user = CustomUser.objects.get(id=id)
    user.is_blocked = False
    user.save()
    return redirect('customers_details',id=user.id)
    