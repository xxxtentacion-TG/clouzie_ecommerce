import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import CustomUser


RESET_SESSION_KEYS = (
    'admin_reset_otp',
    'admin_reset_email',
    'admin_reset_otp_expiry',
    'admin_reset_otp_attempts',
    'admin_reset_otp_sent_at',
    'admin_reset_verified',
)


def _clear_reset_session(request):
    for key in RESET_SESSION_KEYS:
        request.session.pop(key, None)


def _eligible_admin(email):
    return CustomUser.objects.filter(email__iexact=email).filter(
        is_staff=True
    ).first() or CustomUser.objects.filter(email__iexact=email).filter(
        is_superuser=True
    ).first()


def _mask_email(email):
    local, _, domain = email.partition('@')
    return f'{local[:1]}*****@{domain}' if domain else '*****'


def _send_reset_otp(email, otp):
    subject = 'CLOUZIE Admin - Password Reset OTP'
    body = (
        f'Your OTP for admin password reset is: {otp}\n'
        'This OTP is valid for 10 minutes.\n'
        'If you did not request this, please ignore this email.'
    )
    html_message = f"""
    <div style="background:#f5f5f5;padding:36px;font-family:Arial,sans-serif;color:#0a0a0a;">
      <div style="max-width:480px;margin:0 auto;background:#fff;border:1px solid #ebebeb;border-radius:14px;padding:40px 34px;text-align:center;">
        <p style="margin:0 0 30px;font-size:20px;letter-spacing:6px;font-weight:700;">CLOUZIE</p>
        <p style="margin:0 0 10px;font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#a3a3a3;">Admin Password Reset</p>
        <p style="margin:0 0 25px;font-size:14px;line-height:1.65;color:#525252;">Use the verification code below to reset your administrator password.</p>
        <div style="background:#0a0a0a;color:#fff;border-radius:10px;padding:18px;font-size:32px;font-weight:700;letter-spacing:12px;">{otp}</div>
        <p style="margin:24px 0 0;font-size:12px;color:#737373;">Valid for 10 minutes.</p>
        <p style="margin:25px 0 0;padding-top:22px;border-top:1px solid #ebebeb;font-size:11px;line-height:1.6;color:#a3a3a3;">If you did not request this, please ignore this email.</p>
      </div>
    </div>
    """
    send_mail(
        subject,
        body,
        getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
        [email],
        html_message=html_message,
    )


def _issue_otp(request, email):
    otp = str(random.randint(100000, 999999))
    now = timezone.now()
    request.session['admin_reset_otp'] = otp
    request.session['admin_reset_email'] = email
    request.session['admin_reset_otp_expiry'] = (now + timedelta(minutes=10)).isoformat()
    request.session['admin_reset_otp_sent_at'] = now.isoformat()
    request.session['admin_reset_otp_attempts'] = 0
    request.session.pop('admin_reset_verified', None)
    _send_reset_otp(email, otp)


@require_http_methods(['GET', 'POST'])
def admin_forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        admin = _eligible_admin(email)
        generic = 'If this email is registered, you will receive an OTP.'

        if admin:
            _issue_otp(request, admin.email)
            messages.success(request, generic)
            return redirect('adminpanel:admin_verify_otp')

        messages.success(request, generic)

    return render(request, 'adminpanel/auth/forgot_password.html')


@require_http_methods(['GET', 'POST'])
def admin_verify_otp(request):
    email = request.session.get('admin_reset_email')
    if not email:
        return redirect('adminpanel:admin_forgot_password')

    expiry = parse_datetime(request.session.get('admin_reset_otp_expiry', ''))
    sent_at = parse_datetime(request.session.get('admin_reset_otp_sent_at', ''))
    resend_wait = 0
    if sent_at:
        resend_wait = max(0, 60 - int((timezone.now() - sent_at).total_seconds()))

    if request.method == 'POST':
        if not expiry or timezone.now() > expiry:
            _clear_reset_session(request)
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('adminpanel:admin_forgot_password')

        attempts = request.session.get('admin_reset_otp_attempts', 0) + 1
        request.session['admin_reset_otp_attempts'] = attempts
        if attempts > 5:
            _clear_reset_session(request)
            messages.error(request, 'Too many attempts.')
            return redirect('adminpanel:admin_forgot_password')

        submitted_otp = request.POST.get('otp', '').strip()
        if submitted_otp != request.session.get('admin_reset_otp'):
            remaining = max(0, 5 - attempts)
            messages.error(request, f'Incorrect OTP. {remaining} attempts remaining.')
        else:
            request.session['admin_reset_verified'] = True
            return redirect('adminpanel:admin_reset_password')

    return render(request, 'adminpanel/auth/verify_otp.html', {
        'masked_email': _mask_email(email),
        'resend_wait': resend_wait,
        'attempts': request.session.get('admin_reset_otp_attempts', 0),
    })


@require_http_methods(['GET', 'POST'])
def admin_reset_password(request):
    email = request.session.get('admin_reset_email')
    if not email or not request.session.get('admin_reset_verified'):
        return redirect('adminpanel:admin_forgot_password')

    user = _eligible_admin(email)
    if not user:
        _clear_reset_session(request)
        return redirect('adminpanel:admin_forgot_password')

    errors = {}
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not new_password:
            errors['new_password'] = 'Enter a new password.'
        elif len(new_password) < 8:
            errors['new_password'] = 'Password must be at least 8 characters.'
        elif user.check_password(new_password):
            errors['new_password'] = 'New password must be different from your current password.'

        if not confirm_password:
            errors['confirm_password'] = 'Confirm your new password.'
        elif new_password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'

        if not errors:
            user.set_password(new_password)
            user.save(update_fields=['password'])
            if request.user.is_authenticated and request.user.pk == user.pk:
                update_session_auth_hash(request, user)
            _clear_reset_session(request)
            messages.success(request, 'Password reset successfully. Please sign in.', extra_tags='toast')
            return redirect('adminpanel:admin-login')

    return render(request, 'adminpanel/auth/reset_password.html', {'errors': errors})


@require_POST
def admin_resend_otp(request):
    email = request.session.get('admin_reset_email')
    if not email:
        return redirect('adminpanel:admin_forgot_password')

    sent_at = parse_datetime(request.session.get('admin_reset_otp_sent_at', ''))
    if sent_at and (timezone.now() - sent_at).total_seconds() < 60:
        messages.error(request, 'Please wait before requesting a new OTP.')
        return redirect('adminpanel:admin_verify_otp')

    admin = _eligible_admin(email)
    if not admin:
        _clear_reset_session(request)
        return redirect('adminpanel:admin_forgot_password')

    _issue_otp(request, admin.email)
    messages.success(request, 'New OTP sent.')
    return redirect('adminpanel:admin_verify_otp')
