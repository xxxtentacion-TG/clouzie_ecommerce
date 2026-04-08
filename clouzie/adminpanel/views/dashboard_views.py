from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required(login_url="adminpanel:admin-login")
def admin_dashboard(request):
    if request.user.is_authenticated:
        if not request.user.is_admin_user:
            return redirect('home_main')

    return render(request, 'adminpanel/dashboard.html')