from django.shortcuts import render, redirect
from accounts.models import CustomUser
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def admin_login(request):
    if request.user.is_authenticated:
        return redirect('adminpanel:admin-dashboard')

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user_obj = CustomUser.objects.get(email=email)

            user = authenticate(request, email=user_obj.email, password=password)

            if user is not None and user_obj.is_admin_user:
                login(request, user)
                request.session['user_id'] = user.id
                request.session.set_expiry(1209600)
                messages.success(request, "login successfully",extra_tags="toast")
                return redirect('adminpanel:admin-dashboard')

            return render(request, "adminpanel/login.html", {"error": "invalid email or password"})

        except CustomUser.DoesNotExist:
            return render(request, "adminpanel/login.html", {"error": "invalid email or password"})

    return render(request, 'adminpanel/login.html')


def logout_admin(request):
    logout(request)
    messages.success(request, "logout successfully")
    return redirect('adminpanel:admin-login')