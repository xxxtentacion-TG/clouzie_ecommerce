from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')

        if not request.user.is_admin_user:
            messages.error(request, "You are not allowed to access admin panel.")
            return redirect('home_main')

        return view_func(request, *args, **kwargs)

    return wrapper