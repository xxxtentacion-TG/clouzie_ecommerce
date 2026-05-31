import re

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from accounts.models import CustomUser
from adminpanel.utils.admin_gaurd import admin_required


@admin_required
def admin_profile(request):
    return render(request, 'adminpanel/profile/profile.html')


@admin_required
def edit_profile(request):
    user = request.user
    errors = {}

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone_number = request.POST.get('phone_number', '').strip()
        profile_photo = request.FILES.get('profile_photo')

        if not email:
            errors['email'] = 'Email address is required.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = 'Enter a valid email address.'
            else:
                if CustomUser.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                    errors['email'] = 'This email address is already in use.'

        if phone_number and not re.fullmatch(r'\d{10}', phone_number):
            errors['phone_number'] = 'Enter a valid 10-digit phone number.'

        if not errors:
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone_number = phone_number or None
            if profile_photo:
                user.profile_photo = profile_photo
            user.save()
            messages.success(request, 'Admin profile updated successfully.', extra_tags='toast')
            return redirect('adminpanel:admin_profile')

        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone_number': phone_number,
        }
    else:
        form_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': user.phone_number or '',
        }

    return render(request, 'adminpanel/profile/edit_profile.html', {
        'form_data': form_data,
        'errors': errors,
    })


@admin_required
def change_password(request):
    errors = {}

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not current_password:
            errors['current_password'] = 'Enter your current password.'
        elif not request.user.check_password(current_password):
            errors['current_password'] = 'Current password is incorrect.'

        if not new_password:
            errors['new_password'] = 'Enter a new password.'
        elif len(new_password) < 8:
            errors['new_password'] = 'New password must be at least 8 characters.'
        elif current_password and new_password == current_password:
            errors['new_password'] = 'New password must be different from your current password.'

        if not confirm_password:
            errors['confirm_password'] = 'Confirm your new password.'
        elif new_password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'

        if not errors:
            request.user.set_password(new_password)
            request.user.save(update_fields=['password'])
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.', extra_tags='toast')
            return redirect('adminpanel:admin_profile')

    return render(request, 'adminpanel/profile/change_password.html', {'errors': errors})
