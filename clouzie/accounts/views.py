from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from .models import CustomUser,Otp,Address
import re
import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from dotenv import load_dotenv
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.urls import reverse
from adminpanel.models import Products
from wallet.models import Wallet
from adminpanel.models import Banner
import time 
import threading
import math

def send_email_async(email_msg):
    threading.Thread(target=email_msg.send).start()

RESEND_COOLDOWN_SECONDS = 30
MAX_RESEND_ATTEMPTS = 3
MAX_OTP_ATTEMPTS = 5


# Create your views here.

def valid_username(username):
    return re.fullmatch(r'^[A-Za-z0-9]{3,20}$', username)

def valid_email(email):
    return re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def valid_password(password):

    if len(password) < 8:
        return "Password must be at least 8 characters long."

    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter."

    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter."

    if not re.search(r'\d', password):
        return "Password must contain at least one number."

    if not re.search(r'[@$!%*#?&]', password):
        return "Password must contain at least one special character."

    return None


def home(request):
    if request.user.is_authenticated:
        return redirect('home_main')
    new_arrivals = Products.objects.filter(is_active=True,is_deleted=False).order_by('-created_at')[:8]
    banners = [b for b in Banner.objects.filter(is_active=True, is_deleted=False, placement='HOME_HERO').order_by('-created_at') if b.is_valid()]
    return render(request, 'accounts/home.html',{"new_arrivals":new_arrivals, "banners": banners})
@never_cache
def signin(request):
    if request.user.is_authenticated:
        return redirect('home_main')

    if request.method == 'POST':
        lemail = request.POST.get('email')
        lpassword = request.POST.get('password')
        
        try:
            user_obj = CustomUser.objects.get(email=lemail)

            if not user_obj.is_active:
                return render(request, "accounts/login_page.html", {
                    "error": "Please verify your account using OTP before login",
                    "form_data": request.POST
                })

            if user_obj.is_blocked:
                return render(request, "accounts/login_page.html", {
                    "error": "Account is blocked",
                    "form_data": request.POST
                })

            if user_obj.is_admin_user:
                return render(request, "accounts/login_page.html", {
                    "error": "Admin login is not allowed here",
                    "form_data": request.POST
                })

            user = authenticate(request, email=lemail, password=lpassword)

            if user is None:
                return render(request, "accounts/login_page.html", {
                    "error": "Invalid email or password",
                    "form_data": request.POST
                })

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session['user_id'] = user.id
            request.session.set_expiry(1209600)

            messages.success(request, "Logged in successfully", extra_tags='login')
            return redirect('home_main')

        except CustomUser.DoesNotExist:
            return render(request, "accounts/login_page.html", {
                "error": "Invalid email or password",
                "form_data": request.POST
            })

    return render(request, "accounts/login_page.html")

@never_cache
def signup(request):
    ref_code = request.GET.get('ref', '')
    if request.method == 'POST':
        susername = request.POST.get('username', '').strip()
        semail = request.POST.get('email', '').strip().lower()
        spassword = request.POST.get('password', '').strip()
        confirmpassword = request.POST.get('confirmPassword', '').strip()
        sphone = request.POST.get('phone_number', '').strip()
        ref_code_post = (request.POST.get('referral_code', '').strip())

        if not susername and not semail and not spassword and not confirmpassword:
            messages.error(request, 'Please fill all details first.')
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        
        if ref_code_post:
            referrer = CustomUser.objects.filter(referral_code=ref_code_post).first()
            if not referrer:
                messages.error(request, "The referral code entered is invalid. Please double check or leave empty.")
                return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})
            
            
            if referrer.email.strip().lower() == semail or referrer.username.strip().lower() == susername.lower():
                messages.error(request, "You cannot use your own referral code.")
                return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not susername:
            messages.error(request, "Username is required.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})
        
        if ' ' in susername:
            messages.error(request, "Username cannot contain spaces.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not re.match(r'^[a-zA-Z0-9_]+$', susername):
            messages.error(request, "Username can only contain letters, numbers, and underscores.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if len(susername) < 3 or len(susername) > 20:
            messages.error(request, "Username must be between 3 and 20 characters.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if susername.isdigit():
            messages.error(request, "Username cannot contain only numbers.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if len(susername.replace('_', '')) == 0:
            messages.error(request, "Username cannot contain only underscores.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if susername.startswith('_') or susername.endswith('_'):
            messages.error(request, "Username cannot start or end with an underscore.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if '__' in susername:
            messages.error(request, "Username cannot contain consecutive underscores.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not semail:
            messages.error(request, "Email is required.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not valid_email(semail):
            messages.error(request, 'Enter a valid email address.')
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not spassword:
            messages.error(request, "Password is required.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if len(spassword) > 50:
            messages.error(request, "Password is too long.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        password_error = valid_password(spassword)

        if password_error:
            messages.error(request, password_error)
            return render(request, "accounts/signup.html", {"form_data": request.POST,"ref_code": ref_code_post})

        if not confirmpassword:
            messages.error(request, "Please confirm your password.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if spassword != confirmpassword:
            messages.error(request, 'Passwords do not match.')
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not sphone:
            messages.error(request, "Phone number is required.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not sphone.isdigit() or len(sphone) != 10:
            messages.error(request, "Enter a valid 10-digit phone number.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if sphone[0] == '0':
            messages.error(request, "Phone number cannot start with 0.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        existing_user_by_username = CustomUser.objects.filter(username=susername).first()
        if existing_user_by_username:
            if existing_user_by_username.is_active or existing_user_by_username.email != semail:
                messages.error(request, 'Username already taken, choose another.')
                return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        checkuser = CustomUser.objects.filter(email=semail).first()
        if checkuser:
            if checkuser.is_active:
                messages.error(request, 'Email already registered. Please login.')
                return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})
            else:
                checkuser.username = susername
                checkuser.set_password(spassword)
                checkuser.phone_number = sphone
                if ref_code_post:
                    referrer = CustomUser.objects.filter(referral_code=ref_code_post).first()
                    if referrer and referrer != checkuser:
                        checkuser.referred_by = referrer
                checkuser.save()

                otp_code = str(random.randint(100000, 999999))
                expiry_time = timezone.now() + timedelta(minutes=5)
                Otp.objects.filter(user_id=checkuser.id).delete()
                Otp.objects.create(user_id=checkuser.id, code=otp_code, expired_at=expiry_time)
                request.session['otp_expiry'] = expiry_time.timestamp()
                request.session['resend_expiry'] = time.time() + RESEND_COOLDOWN_SECONDS
                request.session['resend_attempts'] = 0
                request.session['otp_attempts'] = 0
                request.session['verify_user_id'] = checkuser.id

                html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
                email = EmailMultiAlternatives(
                    subject="CLOUZIE Verification Code",
                    body=f"Your OTP is {otp_code}",
                    from_email=settings.EMAIL_HOST_USER,
                    to=[checkuser.email],
                )
                email.attach_alternative(html_content, "text/html")
                send_email_async(email)
                return redirect('verify')

        user = CustomUser.objects.create_user(
            username=susername,
            email=semail,
            password=spassword,
            phone_number=sphone,
            is_active=False
        )

        if ref_code_post:
            referrer = CustomUser.objects.filter(referral_code=ref_code_post).first()
            if referrer and referrer != user:
                user.referred_by = referrer
                user.save()

        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)
        Otp.objects.filter(user_id=user.id).delete()
        Otp.objects.create(user_id=user.id, code=otp_code, expired_at=expiry_time)
        request.session['user_id'] = user.id
        request.session['verify_user_id'] = user.id
        request.session['otp_expiry'] = expiry_time.timestamp()
        request.session['resend_expiry'] = time.time() + RESEND_COOLDOWN_SECONDS
        request.session['resend_attempts'] = 0
        request.session['otp_attempts'] = 0

        html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
        email = EmailMultiAlternatives(
            subject="CLOUZIE Verification Code",
            body=f"Your OTP is {otp_code}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        send_email_async(email)
        return redirect('verify')

    return render(request, "accounts/signup.html", {"ref_code": ref_code})


@never_cache
def verify(request):
    user_id = request.session.get('verify_user_id')
    if not user_id:
        return redirect('sigin')

    user = CustomUser.objects.filter(id=user_id).first()
    if not user:
        return redirect('signup')

    if request.method == "POST":
        attempts = request.session.get('otp_attempts', 0)
        if attempts >= MAX_OTP_ATTEMPTS:
            Otp.objects.filter(user_id=user_id).delete()
            request.session.flush()
            messages.error(request, "Too many incorrect attempts. Please register again.")
            return redirect('signup')

        otp_input = ''.join([request.POST.get(f'v{i}', '') for i in range(1, 7)])
        otp_obj = Otp.objects.filter(user_id=user_id).last()

        if not otp_obj:
            messages.error(request, 'Please enter valid OTP')
            return redirect('verify')

        if len(otp_input) != 6:
            messages.error(request, 'Enter complete OTP')
            return redirect('verify')

        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request, 'OTP expired')
            return redirect('verify')

        if otp_input != otp_obj.code:
            attempts += 1
            request.session['otp_attempts'] = attempts
            if attempts >= MAX_OTP_ATTEMPTS:
                Otp.objects.filter(user_id=user_id).delete()
                request.session.flush()
                messages.error(request, "Too many incorrect attempts. Please register again.")
                return redirect('signup')

            remaining = MAX_OTP_ATTEMPTS - attempts
            messages.error(request, f'Incorrect OTP. {remaining} attempt{"s" if remaining != 1 else ""} remaining.')
            return redirect('verify')

        request.session.pop('otp_attempts', None)

        user.is_active = True
        user.save()

        if user.referred_by and not user.referral_reward_given:
            user_wallet, _ = Wallet.objects.get_or_create(user=user)
            referrer_wallet, _ = Wallet.objects.get_or_create(user=user.referred_by)
            user_wallet.credit(50, "Welcome referral reward")
            referrer_wallet.credit(100, f"Referral reward for inviting {user.username}")
            user.referral_reward_given = True
            user.save()

        Otp.objects.filter(user_id=user_id).delete()
        request.session.pop('verify_user_id', None)
        request.session.pop('otp_expiry', None)
        request.session.pop('resend_expiry', None)
        request.session.pop('resend_attempts', None)

        messages.success(request, "Account created successfully")
        return redirect('sigin')

    otp_expiry = request.session.get('otp_expiry', 0)
    resend_expiry = request.session.get('resend_expiry', 0)
    resend_attempts = request.session.get('resend_attempts', 0)
    remaining_seconds = max(0, int(otp_expiry - time.time()))
    resend_remaining_seconds = max(0, math.ceil(resend_expiry - time.time()))
    resend_blocked = resend_attempts >= MAX_RESEND_ATTEMPTS
    initial_minutes = remaining_seconds // 60
    initial_seconds = remaining_seconds % 60
    initial_timer = f"{initial_minutes:01d}:{initial_seconds:02d}"

    return render(request, "accounts/verify.html", {
        "initial_timer": initial_timer,
        "otp_expiry": otp_expiry,
        "resend_remaining_seconds": resend_remaining_seconds,
        "resend_attempts": resend_attempts,
        "max_resend_attempts": MAX_RESEND_ATTEMPTS,
        "resend_blocked": resend_blocked,
    })

@never_cache  
def resend_otp(request):
    if request.method != 'POST':
        return redirect('verify')

    verify_user = request.session.get('verify_user_id') 
    if not verify_user:
        return redirect('sigin')

    resend_attempts = request.session.get('resend_attempts', 0)
    if resend_attempts >= MAX_RESEND_ATTEMPTS:
        messages.error(request, "Maximum resend attempts reached. Please try signup again.")
        return redirect('verify')

    resend_expiry = request.session.get('resend_expiry', 0)
    if time.time() < resend_expiry:
        messages.error(request, "Please wait before requesting a new OTP.")
        return redirect('verify')

    user = CustomUser.objects.filter(id=verify_user).first()
    if not user:
        return redirect('sigin')

    otp_code = str(random.randint(100000, 999999))
    expiry_time = timezone.now() + timedelta(minutes=5)

    Otp.objects.filter(user_id=verify_user).delete()
    Otp.objects.create(user_id=verify_user, code=otp_code, expired_at=expiry_time)

    request.session['otp_expiry'] = expiry_time.timestamp()
    request.session['resend_expiry'] = time.time() + RESEND_COOLDOWN_SECONDS
    request.session['resend_attempts'] = resend_attempts + 1

    html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
    email = EmailMultiAlternatives(
        subject="CLOUZIE Verification Code",
        body=f"Your OTP is {otp_code}",
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email],
    )
    email.attach_alternative(html_content, "text/html")
    send_email_async(email)
    return redirect('verify')

@never_cache 
def forgot_password(request):
    if request.method == 'POST':
        femail = request.POST.get('email', '').strip()

        if not femail:
            return render(request, "accounts/forgot_password.html", {"error": "Email is required","form_data":request.POST})

        if not valid_email(femail):
            return render(request, "accounts/forgot_password.html", {"error": "Enter a valid email address","form_data":request.POST})

        
        user = CustomUser.objects.filter(email=femail).first()
        if not user:
            return render(request, "accounts/forgot_password.html", {"error": "No account found with this email address.", "form_data": request.POST})

        if not user.is_active:
            return render(request, "accounts/forgot_password.html", {"error": "This account is not verified yet. Please complete your registration first.", "form_data": request.POST})

        if user.is_blocked:
            return render(request, "accounts/forgot_password.html", {"error": "This account has been suspended. Please contact support.", "form_data": request.POST})

        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)

        request.session['reset_email'] = femail
        request.session['forgot_user_id'] = user.id
        request.session['forgot_otp_expiry'] = expiry_time.timestamp()  # ✅ for timer

        Otp.objects.filter(user_id=user.id).delete()
        Otp.objects.create(code=otp_code, expired_at=expiry_time, user_id=user.id)

        html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
        email = EmailMultiAlternatives(
            subject="CLOUZIE Verification Code",
            body=f"Your OTP is {otp_code}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        send_email_async(email)

        return redirect('forgot_verify')

    return render(request, "accounts/forgot_password.html")


@never_cache
def forgot_verify(request):
    forgot_user = request.session.get('forgot_user_id')
    if not forgot_user:
        return redirect('sigin')

    if request.method == 'POST':
        Otp_input = ''.join([request.POST.get(f'v{i}', '') for i in range(1, 7)])
        user_id = request.session.get('forgot_user_id')
        otp_obj = Otp.objects.filter(user_id=user_id).first()

        if not Otp_input or len(Otp_input) != 6:
            messages.error(request, "Please enter the complete 6-digit verification code.")
            return redirect('forgot_verify')

        if not otp_obj:
            messages.error(request, "OTP not found. Please request a new one.")
            return redirect('forgot_verify')

        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request, "Your verification code has expired. Please request a new one.")
            return redirect('forgot_verify')

        if otp_obj.code != Otp_input:
            messages.error(request, "The verification code you entered is incorrect. Please try again.")
            return redirect('forgot_verify')

        return redirect("reset_password")

    import time
    otp_expiry = request.session.get('forgot_otp_expiry', 0)
    remaining_seconds = max(0, int(otp_expiry - time.time()))
    initial_minutes = remaining_seconds // 60
    initial_seconds = remaining_seconds % 60
    initial_timer = f"{initial_minutes}:{initial_seconds:02d}"

    return render(request, "accounts/forgot_verify.html", {"initial_timer": initial_timer})


def forgot_resend_otp(request):
    if request.method == "POST":
        email = request.session.get("reset_email")
        if not email:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Session expired."}, status=400)
            return redirect("forgot_verify")

        user = CustomUser.objects.filter(email=email).first()
        if not user:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "User not found."}, status=404)
            return redirect("forgot_verify")

        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)

        Otp.objects.filter(user_id=user.id).delete()
        Otp.objects.create(code=otp_code, expired_at=expiry_time, user_id=user.id)

        request.session['forgot_otp_expiry'] = expiry_time.timestamp()

        html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
        email_msg = EmailMultiAlternatives(
            subject="CLOUZIE Verification Code",
            body=f"Your OTP is {otp_code}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email_msg.attach_alternative(html_content, "text/html")
        send_email_async(email_msg)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "redirect_url": reverse("forgot_verify"),
                "otp_expiry": request.session["forgot_otp_expiry"],
            })

    return redirect("forgot_verify")


@never_cache
def rest_password(request):
    forgot_user = request.session.get('forgot_user_id')
    if not forgot_user:
        return redirect('sigin')

    if request.method == 'POST':
        rpassword  = request.POST.get('password')
        cpassword  = request.POST.get('cnfmpassword')
        remail     = request.session.get('reset_email')
        user       = CustomUser.objects.filter(email=remail).first()

        if not user:
            return redirect('sigin')

        if rpassword != cpassword:
            return render(request, "accounts/reset_password.html",
                {"error": "The passwords you entered do not match. Please try again."})

        password_error = valid_password(rpassword)
        if password_error:
            messages.error(request, password_error)
            return render(request, "accounts/reset_password.html", {"form_data": request.POST})

        user.set_password(rpassword)
        user.save()

        request.session.pop('forgot_user_id', None)
        request.session.pop('reset_email', None)
        request.session.pop('forgot_otp_expiry', None)

        Otp.objects.filter(user_id=user.id).delete()

        messages.success(request, "Password reset successfully. Please log in.")
        return redirect('sigin')

    return render(request, "accounts/reset_password.html")
@login_required
def main_home(request):
    if request.user.is_authenticated:
        if request.user.is_admin_user:
            return redirect('adminpanel:admin-dashboard')
    new_arrivals = Products.objects.filter(is_active=True,is_deleted=False).order_by('-created_at')[:8]
    banners = [b for b in Banner.objects.filter(is_active=True, is_deleted=False, placement='HOME_HERO').order_by('-created_at') if b.is_valid()]
    return render(request,'accounts/main_page.html',{"new_arrivals":new_arrivals, "banners": banners})

def about(request):
    return render(request, 'accounts/about.html')

def contact(request):
    return render(request, 'accounts/contact.html')

@login_required()
@never_cache
def profile(request):  
    return render(request,"accounts/profile.html",{"user":request.user}) 

@login_required
@never_cache
def change_password(request):
    
    if request.method == "POST":
        user = request.user
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        cnfrm_password = request.POST.get('confirm_password')
        if not old_password and new_password and cnfrm_password:
            messages.error(request, "Please complete all required fields before continuing.")
            return render(request, "accounts/change_password.html", {"form_data": request.POST})
        
        if not user.check_password(old_password):
            messages.error(request, "The current password you entered is incorrect.")
            return render(request, "accounts/change_password.html", {"form_data": request.POST})
        
        if new_password != cnfrm_password:
            messages.error(request, "New password and confirmation do not match.")
            return render(request, "accounts/change_password.html", {"form_data": request.POST})
        
        password_error = valid_password(new_password)

        if password_error:
            messages.error(request, password_error)
            return render(request, "accounts/change_password.html", {"form_data": request.POST})
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request,user)
        messages.success(request,"Password changed successfully")
        return redirect('change_password')
    
    return render(request,'accounts/change_password.html') 


import base64
from django.core.files.base import ContentFile

@login_required
@never_cache
def edit_profile(request):
    user = request.user
    user_details = CustomUser.objects.get(id=user.id)

    if request.method == 'POST':
        username = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip().lower()
        remove_photo = request.POST.get('remove_photo', '').strip()

        image = None
        cropped_data = request.POST.get('cropped_image_data', '').strip()
        if cropped_data and cropped_data.startswith('data:image'):
            try:
                fmt, imgstr = cropped_data.split(';base64,')
                ext = fmt.split('/')[-1]
                image = ContentFile(
                    base64.b64decode(imgstr),
                    name=f'profile_{user.id}.{ext}'
                )
            except Exception as e:
                messages.error(request, "Invalid image data. Please try again.")
                return redirect('edit_profile')
        else:
            image = request.FILES.get('profile_image')

        if not username or not phone or not email:
            messages.error(request, "All fields are required.")
            return redirect('edit_profile')

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messages.error(request, "Username can only contain letters, numbers, and underscores.")
            return redirect('edit_profile')
        if len(username) < 3 or len(username) > 20:
            messages.error(request, "Username must be between 3 and 20 characters.")
            return redirect('edit_profile')
        if username.isdigit():
            messages.error(request, "Username cannot contain only numbers.")
            return redirect('edit_profile')
        if username.startswith('_') or username.endswith('_'):
            messages.error(request, "Username cannot start or end with an underscore.")
            return redirect('edit_profile')
        if '__' in username:
            messages.error(request, "Username cannot contain consecutive underscores.")
            return redirect('edit_profile')

        if not phone.isdigit():
            messages.error(request, "Phone number must contain only digits.")
            return redirect('edit_profile')
        if len(phone) != 10:
            messages.error(request, "Phone number must be exactly 10 digits.")
            return redirect('edit_profile')
        if phone[0] == '0':
            messages.error(request, "Phone number cannot start with 0.")
            return redirect('edit_profile')
        if set(phone) == {'0'}:
            messages.error(request, "Enter a valid phone number.")
            return redirect('edit_profile')

        if not valid_email(email):
            messages.error(request, "Enter a valid email address.")
            return redirect('edit_profile')

        if image is not None and image.size > 2 * 1024 * 1024:
            messages.error(request, "Image size must be under 2MB.")
            return redirect('edit_profile')

        no_change = (
            user.username == username and
            user.phone_number == phone and
            user.email == email and
            image is None and
            not remove_photo
        )
        if no_change:
            messages.error(request, "No changes made.")
            return redirect('edit_profile')

        if username != user.username:
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists, choose another.')
                return redirect('edit_profile')

        if email != user.email:
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return redirect('edit_profile')

            if remove_photo and image is None:
                if user.profile_photo:
                    user.profile_photo.delete(save=False)
                user.profile_photo = None
            elif image is not None:
                if user.profile_photo:
                    user.profile_photo.delete(save=False)
                user.profile_photo = image

            user.username = username
            user.phone_number = phone
            user.save()

            Otp.objects.filter(user_id=user.id).delete()
            request.session['email_user_id'] = user.id
            request.session['email_id'] = email
            request.session['pending_username'] = username
            request.session['pending_phone'] = phone

            otp_code = str(random.randint(100000, 999999))
            expiry_time = timezone.now() + timedelta(minutes=5)
            Otp.objects.create(code=otp_code, expired_at=expiry_time, user_id=user.id)
            request.session['email_otp_expiry'] = time.time() + 305
            request.session['email_resend_expiry'] = time.time() + 30

            html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
            email_msg = EmailMultiAlternatives(
                subject="CLOUZIE Verification Code",
                body=f"Your OTP is {otp_code}",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )
            email_msg.attach_alternative(html_content, "text/html")
            send_email_async(email_msg)
            return redirect('email_verify')

        if remove_photo and image is None:
            if user.profile_photo:
                user.profile_photo.delete(save=False)
            user.profile_photo = None
        elif image is not None:
            if user.profile_photo:
                user.profile_photo.delete(save=False)
            user.profile_photo = image

        user.username = username
        user.phone_number = phone
        user.save()
        messages.success(request, "Profile updated successfully")
        return redirect('profile')

    return render(request, "accounts/edit_profile.html", {"user": user_details})


@login_required
@never_cache
def email_verify(request):
    import time
    user_id = request.session.get('email_user_id')
    user = get_object_or_404(CustomUser, id=user_id)

    clear_storage = request.session.pop('clear_otp_storage', False)
    reset_timers = request.session.pop('reset_otp_timers', False)

    if request.method == "POST":
        Otp_input = ''.join([request.POST.get(f'v{i}', '') for i in range(1, 7)])
        otp_obj = Otp.objects.filter(user_id=user_id).first()

        if len(Otp_input) != 6:
            messages.error(request, "Please enter the complete 6-digit verification code.")
            return redirect('email_verify')

        if not otp_obj:
            messages.error(request, "OTP not found. Please request a new one.")
            return redirect('email_verify')

        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request, "Your verification code has expired.")
            return redirect('email_verify')

        if otp_obj.code != Otp_input:
            messages.error(request, "The verification code you entered is incorrect.")
            return redirect('email_verify')

        Otp.objects.filter(user_id=user_id).delete()

        user.email = request.session.get('email_id')
        user.username = request.session.get('pending_username', user.username)
        user.phone_number = request.session.get('pending_phone', user.phone_number)
        user.save()

        request.session.pop('email_user_id', None)
        request.session.pop('email_id', None)
        request.session.pop('pending_username', None)
        request.session.pop('pending_phone', None)
        request.session.pop('email_otp_expiry', None)

        messages.success(request, "Profile updated successfully")
        return redirect('profile')

    otp_expiry = request.session.get('email_otp_expiry', 0)
    resend_expiry = request.session.get('email_resend_expiry', 0)

    remaining_seconds = max(0, int(otp_expiry - time.time()))
    resend_remaining = max(0, int(resend_expiry - time.time()))

    initial_minutes = remaining_seconds // 60
    initial_seconds = remaining_seconds % 60
    initial_timer = f"{initial_minutes}:{initial_seconds:02d}"

    return render(request, "accounts/email_verify.html", {
        "initial_timer": initial_timer,
        "resend_timer": resend_remaining,   
    })
    

@login_required
@never_cache
def email_resend_otp(request):
    if request.method == 'POST':
        user_id = request.session.get('email_user_id')
        if not user_id:
            return redirect('edit_profile')

        user = get_object_or_404(CustomUser, id=user_id)

        Otp.objects.filter(user_id=user_id).delete()

        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)
        Otp.objects.create(code=otp_code, expired_at=expiry_time, user_id=user_id)

        
        request.session['email_otp_expiry'] = time.time() + 305
        request.session['email_resend_expiry'] = time.time() + 30

        
        html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
        email_msg = EmailMultiAlternatives(
            subject="CLOUZIE Verification Code",
            body=f"Your OTP is {otp_code}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email_msg.attach_alternative(html_content, "text/html")
        send_email_async(email_msg)

        messages.success(request, "A new verification code has been sent.")
        return redirect('email_verify')

    return redirect('email_verify')


@login_required
@never_cache
def remove_profile(request):
    user = request.user
    if user.profile_photo:
         user.profile_photo.delete(save=False)
         
    user.profile_photo = None
    user.save()
    return redirect('edit_profile')

def logout_page(request):
    logout(request)
    messages.error(request, "You have been logged out")
    return redirect('home')
   
@login_required
@never_cache
def adress(request):
    address = Address.objects.filter(user=request.user).order_by('-is_default')
    return render(request,"accounts/address.html",{"address":address})

@login_required
@never_cache
def add_address(request):
    addresses = Address.objects.filter(user=request.user)
    if request.method == "POST":
        value = False
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        address_line1 = request.POST.get('address_line1', '').strip()
        address_line2 = request.POST.get('address_line2', '').strip()
        is_default = bool(request.POST.get('is_default'))
        address_type = request.POST.get('type')
        
        if not addresses.exists():
            value = True
            
        if is_default:
            Address.objects.filter(user_id=request.user).update(is_default=False)
            value = is_default
            
            
        fields = [
        "full_name", "phone_number", "address_line1",
        "city", "state", "pincode"
        ]

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        for field in fields:
            if not request.POST.get(field):
                if is_ajax: return JsonResponse({'status': 'error', 'message': 'Please fill all required fields.'})
                messages.error(request,"fill the address first")
                return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})
        

        if not full_name:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Full name is required'})
            messages.error(request,"Full name is required")
            return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})
        
        elif not re.match(r'^[A-Za-z ]+$', full_name):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Name can only contain letters and spaces'})
            messages.error(request,"Name can only contain letters and spaces")
            return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})
        
        if not pincode.isdigit():
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Pincode must contain only digits'})
            messages.error(request, "Pincode must contain only digits")
            return render(request, "accounts/add_address.html", locals())
        
        if len(pincode) != 6:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Incorrect pin Code'})
            messages.error(request,"Incorrect pin Code")
            return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})
        
        if not phone_number.isdigit():
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Phone number must contain only digits'})
            messages.error(request, "Phone number must contain only digits")
            return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})

        if phone_number.startswith('0'):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Phone number cannot start with 0'})
            messages.error(request, "Phone number cannot start with 0")
            return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})

        if len(phone_number) != 10:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Mobile number must be 10 digits'})
            messages.error(request,"mobile number is not 10 digit")
            return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})
        

        if not re.match(r'^[A-Za-z ]+$', city):
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'City can only contain letters and spaces'})
            messages.error(request, "City can only contain letters and spaces")
            return render(request, "accounts/add_address.html", locals())


        if not re.match(r'^[A-Za-z ]+$', state):
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'State can only contain letters and spaces'})
            messages.error(request, "State can only contain letters and spaces")
            return render(request, "accounts/add_address.html", locals())


        if len(address_line1) < 5:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Address line 1 must be at least 5 characters'})
            messages.error(request, "Address line 1 must be at least 5 characters")
            return render(request, "accounts/add_address.html", locals())
    

        if re.fullmatch(r'[^A-Za-z0-9]+', address_line1):
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'House / building / street address cannot contain only special characters'})
            messages.error(request, "House / building / street address cannot contain only special characters")
            return render(request, "accounts/add_address.html", locals())

        if not re.search(r'[A-Za-z0-9]', address_line1):
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Enter a valid house, building, or street address'})
            messages.error(request, "Enter a valid house, building, or street address")
            return render(request, "accounts/add_address.html", locals())


        if address_line2:
            if len(address_line2) < 3:
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Landmark must be at least 3 characters'})
                messages.error(request, "Landmark must be at least 3 characters")
                return render(request, "accounts/add_address.html", locals())

            if re.fullmatch(r'[^A-Za-z0-9]+', address_line2):
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Landmark cannot contain only special characters'})
                messages.error(request, "Landmark cannot contain only special characters")
                return render(request, "accounts/add_address.html", locals())

            if not re.search(r'[A-Za-z0-9]', address_line2):
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Enter a valid landmark'})
                messages.error(request, "Enter a valid landmark")
                return render(request, "accounts/add_address.html", locals())
        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone_number,
            pincode=pincode,
            city=city,
            state=state,
            address_line1=address_line1,
            address_line2=address_line2,
            is_default = value,
            type = address_type   
        )
        if is_ajax:
            return JsonResponse({'status': 'success', 'message': 'Address added successfully'})
        messages.success(request,"Address added successfully")
        return redirect('address')
    return render(request,"accounts/add_address.html")
@login_required
@never_cache
def edit_address(request,id):
    address = get_object_or_404(Address,id=id,user=request.user)
    addressess = Address.objects.filter(id=id,user=request.user)
    if request.method == "POST":
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        
        
        check_is_default = bool(request.POST.get('is_default'))
        if (
        address.full_name == request.POST.get('full_name') and
        address.phone_number == request.POST.get('phone_number') and
        address.pincode == request.POST.get('pincode') and
        address.city == request.POST.get('city') and
        address.state == request.POST.get('state') and
        address.address_line1 == request.POST.get('address_line1') and
        address.address_line2 == request.POST.get('address_line2') and
        address.is_default == check_is_default and
        address.type == request.POST.get('type')
        ):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'No changes were made'})
            messages.error(request,"no changes")
            return redirect('edit_address',id=address.id)
        
            
        is_default = request.POST.get('is_default') == 'on'
        address.full_name = request.POST.get('full_name', '').strip()
        address.phone_number = request.POST.get('phone_number', '').strip()
        address.pincode = request.POST.get('pincode', '').strip()
        address.city = request.POST.get('city', '').strip()
        address.state = request.POST.get('state', '').strip()
        address.address_line1 = request.POST.get('address_line1', '').strip()
        address.address_line2 = request.POST.get('address_line2', '').strip()
        address.is_default = bool(request.POST.get('is_default'))
        address.type = request.POST.get('type')
        
        if not address.full_name:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Full name is required'})
            messages.error(request, "Full name is required")
            return render(request, "accounts/edit_address.html", {"address": address})

        elif not re.match(r'^[A-Za-z ]+$', address.full_name):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Name can only contain letters and spaces'})
            messages.error(request, "Name can only contain letters and spaces")
            return render(request, "accounts/edit_address.html", {"address": address})

        if not address.pincode.isdigit():
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Pincode must contain only digits'})
            messages.error(request, "Pincode must contain only digits")
            return render(request, "accounts/edit_address.html", {"address": address})

        if len(address.pincode) != 6:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Incorrect pin Code'})
            messages.error(request, "Incorrect pin Code")
            return render(request, "accounts/edit_address.html", {"address": address})

        if not address.phone_number.isdigit():
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Phone number must contain only digits'})
            messages.error(request, "Phone number must contain only digits")
            return render(request, "accounts/edit_address.html", {"address": address})

        if address.phone_number.startswith('0'):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Phone number cannot start with 0'})
            messages.error(request, "Phone number cannot start with 0")
            return render(request, "accounts/edit_address.html", {"address": address})

        if len(address.phone_number) != 10:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Mobile number must be 10 digits'})
            messages.error(request, "Mobile number must be 10 digits")
            return render(request, "accounts/edit_address.html", {"address": address})

        if not re.match(r'^[A-Za-z ]+$', address.city):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'City can only contain letters and spaces'})
            messages.error(request, "City can only contain letters and spaces")
            return render(request, "accounts/edit_address.html", {"address": address})

        if not re.match(r'^[A-Za-z ]+$', address.state):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'State can only contain letters and spaces'})
            messages.error(request, "State can only contain letters and spaces")
            return render(request, "accounts/edit_address.html", {"address": address})

        if len(address.address_line1) < 5:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Address line 1 must be at least 5 characters'})
            messages.error(request, "Address line 1 must be at least 5 characters")
            return render(request, "accounts/edit_address.html", {"address": address})

        if re.fullmatch(r'[^A-Za-z0-9]+', address.address_line1):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'House / building / street address cannot contain only special characters'})
            messages.error(request, "House / building / street address cannot contain only special characters")
            return render(request, "accounts/edit_address.html", {"address": address})

        if not re.search(r'[A-Za-z0-9]', address.address_line1):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Enter a valid house, building, or street address'})
            messages.error(request, "Enter a valid house, building, or street address")
            return render(request, "accounts/edit_address.html", {"address": address})

        if address.address_line2:
            if len(address.address_line2) < 3:
                if is_ajax: return JsonResponse({'status': 'error', 'message': 'Landmark must be at least 3 characters'})
                messages.error(request, "Landmark must be at least 3 characters")
                return render(request, "accounts/edit_address.html", {"address": address})

            if re.fullmatch(r'[^A-Za-z0-9]+', address.address_line2):
                if is_ajax: return JsonResponse({'status': 'error', 'message': 'Landmark cannot contain only special characters'})
                messages.error(request, "Landmark cannot contain only special characters")
                return render(request, "accounts/edit_address.html", {"address": address})

            if not re.search(r'[A-Za-z0-9]', address.address_line2):
                if is_ajax: return JsonResponse({'status': 'error', 'message': 'Enter a valid landmark'})
                messages.error(request, "Enter a valid landmark")
                return render(request, "accounts/edit_address.html", {"address": address})
        
        if not Address.objects.filter(user=request.user).exclude(id=address.id).exists():
            address.is_default = True
            
        if is_default:
            Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)
            address.is_default = True
            
        address.save()
        if is_ajax:
            return JsonResponse({'status': 'success', 'message': 'Address updated successfully'})
        messages.success(request,"address updated successfully")
        return redirect('address')
    return render(request,"accounts/edit_address.html",{"address":address})
@login_required
@never_cache
def delete_address(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if address.is_default:
        new = Address.objects.filter(user=request.user).exclude(id=id).first()
        if new:
            new.is_default = True
            new.save()

    address.delete()

    if is_ajax:
        
        new_default = Address.objects.filter(user=request.user).filter(is_default=True).first()
        return JsonResponse({
            'status': 'success',
            'message': 'Address deleted successfully',
            'new_default_id': new_default.id if new_default else None,
        })
    return redirect('address')

@login_required
@never_cache
def referral_page(request):
    user = request.user
    referred_users = user.referrals.all().order_by('-date_joined')

    total_referrals    = referred_users.count()
    successful         = referred_users.filter(referral_reward_given=True).count()
    pending            = total_referrals - successful

    referral_url = f"{request.scheme}://{request.get_host()}/signup?ref={user.referral_code}"

    return render(request, "accounts/referral.html", {
        "user": user,
        "referred_users": referred_users,
        "total_referrals": total_referrals,
        "successful": successful,
        "pending": pending,
        "referral_url": referral_url,
    })

def temp(request):
    return render(request,"accounts/temp.html")

def custom_404(request, exception):
    return render(request, 'base/404.html', status=404)
