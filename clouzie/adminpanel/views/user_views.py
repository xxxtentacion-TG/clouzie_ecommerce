from django.shortcuts import render, redirect
from accounts.models import CustomUser, Address
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required

@login_required(login_url="adminpanel:admin-login")
def users(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    query = request.GET.get('q', '').strip()
    users = CustomUser.objects.all().order_by('-created_at').exclude(is_admin_user=True)

    status = request.GET.get('status')

    if query:
        users = CustomUser.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    if status == 'Active':
        users = CustomUser.objects.filter(is_blocked=False)

    elif status == 'inactive':
        users = CustomUser.objects.filter(is_blocked=True)

    paginator = Paginator(users, 5)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    return render(request, "adminpanel/users/list.html", {"users": users})


@login_required(login_url="adminpanel:admin-login")
def users_details(request, id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    user_obj = CustomUser.objects.get(id=id)
    address = Address.objects.filter(user_id=user_obj.id, is_default=True).first()

    return render(request, "adminpanel/users/details.html", {
        'user_obj': user_obj,
        "address": address
    })


@login_required(login_url="adminpanel:admin-login")
def customer_block(request, id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    user = CustomUser.objects.get(id=id)

    if request.method == "POST":
        user.is_blocked = True
        user.save()
        return redirect('adminpanel:customers')

    return render(request, "adminpanel/users/confirm_action.html", {
        "user_obj": user,
        "action": "block"
    })


@login_required(login_url="adminpanel:admin-login")
def customer_unblock(request, id):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')
        
    user = CustomUser.objects.get(id=id)

    if request.method == "POST":
        user.is_blocked = False
        user.save()
        return redirect('adminpanel:customers')

    return render(request, "adminpanel/users/confirm_action.html", {
        "user_obj": user,
        "action": "unblock"
    })