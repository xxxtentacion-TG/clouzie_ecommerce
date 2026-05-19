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
from adminpanel.models import Products
from wallet.models import Wallet
from adminpanel.models import Banner
import time

# Create your views here.

def valid_username(username):
    return re.fullmatch(r'^[A-Za-z0-9]{3,20}$', username)

def valid_email(email):
    return re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def valid_password(password):
    return re.fullmatch(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$', password)


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
        
            user = authenticate(request,email=user_obj.email,password=lpassword)
            if user_obj.is_blocked:
                return render(request,"accounts/login_page.html",{"error":"Account is Blocked",'form_data':request.POST})
            
            if user_obj.is_admin_user:
                return render(request,"accounts/login_page.html",{"error":"Admin not Allowed","form_data":request.POST})
            if user is not None:
                login(request,user)
                request.session['user_id'] = user.id
                request.session.set_expiry(1209600)
                messages.success(request, "Logged in successfully",extra_tags='login')
                return redirect('home_main')
            return render(request,"accounts/login_page.html",{"error":"invalid email or password","form_data":request.POST})
        
        except CustomUser.DoesNotExist:
            return render(request,"accounts/login_page.html",{"error":"invalid email or password","form_data":request.POST})
          
    return render(request,"accounts/login_page.html")

@never_cache
def signup(request):
    ref_code = request.GET.get('ref', '')
    if request.method == 'POST':
        susername = request.POST.get('username', '').strip()
        semail = request.POST.get('email', '').strip().lower()
        spassword = request.POST.get('password', '').strip()
        confirmpassword = request.POST.get('confirmPassword', '').strip()
        ref_code_post = request.POST.get('referral_code', '').strip() or request.GET.get('ref', '').strip()

        if not susername and not semail and not spassword and not confirmpassword:
            messages.error(request, 'Please fill all details first.')
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not susername:
            messages.error(request, "Username is required.")
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

        if not valid_password(spassword):
            messages.error(request, 'Password must be 6+ chars with letters & numbers.')
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if not confirmpassword:
            messages.error(request, "Please confirm your password.")
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if spassword != confirmpassword:
            messages.error(request, 'Passwords do not match.')
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        if CustomUser.objects.filter(username=susername).exists():
            messages.error(request, 'Username already taken, choose another.')
            return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})

        checkuser = CustomUser.objects.filter(email=semail).first()
        if checkuser:
            if checkuser.is_active:
                messages.error(request, 'Email already registered. Please login.')
                return render(request, "accounts/signup.html", {"form_data": request.POST, "ref_code": ref_code_post})
            else:
                otp_code = str(random.randint(100000, 999999))
                expiry_time = timezone.now() + timedelta(minutes=5)
                Otp.objects.filter(user_id=checkuser.id).delete()
                Otp.objects.create(user_id=checkuser.id, code=otp_code, expired_at=expiry_time)
                request.session['otp_expiry'] = expiry_time.timestamp()
                request.session['resend_expiry'] = time.time() + 30
                request.session['verify_user_id'] = checkuser.id

                html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
                email = EmailMultiAlternatives(
                    subject="CLOUZIE Verification Code",
                    body=f"Your OTP is {otp_code}",
                    from_email=settings.EMAIL_HOST_USER,
                    to=[checkuser.email],
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                return redirect('verify')

        user = CustomUser.objects.create_user(
            username=susername,
            email=semail,
            password=spassword,
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
        request.session['resend_expiry'] = time.time() + 30

        html_content = render_to_string("accounts/email/otp_email.html", {"otp": otp_code})
        email = EmailMultiAlternatives(
            subject="CLOUZIE Verification Code",
            body=f"Your OTP is {otp_code}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
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
        otp_input = ''.join([
            request.POST.get(f'v{i}', '')
            for i in range(1, 7)
        ])

        otp_obj = Otp.objects.filter(user_id=user_id).last()

        if not otp_obj:
            messages.error(request, 'Please enter valid OTP')
            return redirect('verify')

        if len(otp_input) != 6:
            messages.error(request, 'Enter complete OTP')
            return redirect('verify')

        if otp_input != otp_obj.code:
            messages.error(request, 'Incorrect OTP')
            return redirect('verify')

        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request, 'OTP expired')
            return redirect('verify')

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

        messages.success(request, "Account created successfully")
        return redirect('sigin')

    otp_expiry = request.session.get('otp_expiry', 0)
    resend_expiry = request.session.get('resend_expiry', 0)

    remaining_seconds = max(0, int(otp_expiry - time.time()))
    resend_remaining = max(0, int(resend_expiry - time.time()))

    initial_minutes = remaining_seconds // 60
    initial_seconds = remaining_seconds % 60
    initial_timer = f"{initial_minutes:01d}:{initial_seconds:02d}"

    return render(request, "accounts/verify.html", {
        "initial_timer": initial_timer,
        "otp_expiry": otp_expiry,
        "resend_timer": resend_remaining,
    })

@never_cache  
def resend_otp(request):
    verify_user = request.session.get('verify_user_id')
    expiry_time = timezone.now() + timedelta(minutes=5)
    request.session['otp_expiry'] = expiry_time.timestamp()
    if not verify_user:
        return redirect('sigin')
    
    user_id = request.session.get('user_id')
    Otp.objects.filter(user_id=user_id).delete()
    
    
    otp_code = str(random.randint(100000, 999999))
    expiry_time = timezone.now() + timedelta(minutes=5)
    user = CustomUser.objects.get(id=user_id)
    Otp.objects.create(
    user_id=user_id,              
    code=otp_code,
    expired_at=expiry_time
    )

    html_content = render_to_string(
        "accounts/email/otp_email.html",
        {"otp": otp_code}
        )

    email = EmailMultiAlternatives(
    subject="CLOUZIE Verification Code",
    body=f"Your OTP is {otp_code}",
    from_email=settings.EMAIL_HOST_USER,
    to=[user.email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()
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
            return render(request, "accounts/forgot_password.html", {"error": "No account found with this email address.","form_data":request.POST})

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
        email.send()

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
            return redirect("forgot_verify")

        user = CustomUser.objects.filter(email=email).first()
        if not user:
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
        email_msg.send()

    return redirect("forgot_verify")
@never_cache
def rest_password(request):
    forgot_user = request.session.get('forgot_user_id')
    if not forgot_user:
        return redirect('sigin')
    
    if request.method == 'POST':
        rpassword = request.POST.get('password')
        cpassword = request.POST.get('cnfmpassword')
        remail = request.session.get('reset_email')
        user = CustomUser.objects.filter(email=remail).first()
        otp_obj = Otp.objects.filter(user_id=user.id).first()
        if rpassword != cpassword:
            return render(request,"accounts/reset_password.html",{"error":"The passwords you entered do not match. Please try again."})
        
        if not valid_password(rpassword):
            return render(request,"accounts/reset_password.html",{"error":"Password must be 6+ chars with letters & numbers"})
        if not valid_password(cpassword):
            return render(request,"accounts/reset_password.html",{"error":"Password must be 6+ chars with letters & numbers"})
        user.set_password(rpassword)
        user.save()
        request.session.pop('forgot_user_id',None)
        otp_obj.delete()
        return redirect('sigin')
    return render(request,"accounts/reset_password.html")
@login_required
def main_home(request):
    if request.user.is_authenticated:
        if request.user.is_admin_user:
            return redirect('adminpanel:admin-dashboard')
    new_arrivals = Products.objects.filter(is_active=True,is_deleted=False).order_by('-created_at')[:8]
    banners = [b for b in Banner.objects.filter(is_active=True, is_deleted=False, placement='HOME_HERO').order_by('-created_at') if b.is_valid()]
    return render(request,'accounts/main_page.html',{"new_arrivals":new_arrivals, "banners": banners})
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
            return redirect('changepassword')
        if not user.check_password(old_password):
            messages.error(request, "The current password you entered is incorrect.")
            return redirect('change_password')
        
        if new_password != cnfrm_password:
            messages.error(request, "New password and confirmation do not match.")
            return redirect('change_password')
        if not valid_password(new_password):
            messages.error(request, "Your new password does not meet security requirements.")
            return redirect('change_password')
        if not valid_password(cnfrm_password):
            messages.error(request, "Please enter a valid confirmation password.")
            return redirect('change_password')
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request,user)
        messages.success(request,"Password changed successfully")
        return redirect('change_password')
    
    return render(request,'accounts/change_password.html') 


@login_required
@never_cache
def edit_profile(request):
    user = request.user
    user_details = CustomUser.objects.get(id=user.id)
    if request.method == 'POST':
        username = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip().lower()
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

        
        no_change = (
            user.username == username and
            user.phone_number == phone and
            user.email == email and
            image is None
        )
        if no_change:
            messages.error(request, "No changes made.")
            return redirect('edit_profile')

       
        if username != user.username:
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists, choose another.')
                return redirect('edit_profile')

        
        if image is not None:
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']
            max_size = 2 * 1024 * 1024  
            if image.content_type not in allowed_types:
                messages.error(request, "Only JPEG, PNG, and WEBP images are allowed.")
                return redirect('edit_profile')
            if image.size > max_size:
                messages.error(request, "Image size must be under 2MB.")
                return redirect('edit_profile')

        if email != user.email:
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return redirect('edit_profile')

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
            email_msg.send()
            return redirect('email_verify')

        # Save image
        if image is not None:
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
        email_msg.send()

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
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        pincode = request.POST.get('pincode')
        city = request.POST.get('city') 
        state = request.POST.get('state') 
        address_line1 = request.POST.get('address_line1') 
        address_line2 = request.POST.get('address_line2') 
        is_default = bool(request.POST.get('is_default'))
        address_type = request.POST.get('type')
        
        if not addresses.exists():
            value = True
            
        if is_default:
            Address.objects.filter(user_id=request.user).update(is_default=False)
            value = is_default
            
            
        fields = [
        "full_name", "phone_number", "address_line1","address_line2",
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
            return redirect('add_address')
        
        elif not re.match(r'^[A-Za-z ]+$', full_name):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Name can only contain letters and spaces'})
            messages.error(request,"Name can only contain letters and spaces")
            return redirect('add_address')

        if len(pincode) != 6:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Incorrect pin Code'})
            messages.error(request,"Incorrect pin Code")
            return redirect('add_address')
        
        if len(phone_number) != 10:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Mobile number must be 10 digits'})
            messages.error(request,"mobile number is not 10 digit")
            return redirect('add_address')
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
        
        # is_default == bool(request.POST.get('is_default'))
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
        address.full_name  = request.POST.get('full_name')
        address.phone_number = request.POST.get('phone_number')
        address.pincode = request.POST.get('pincode')
        address.city = request.POST.get('city') 
        address.state = request.POST.get('state') 
        address.address_line1 = request.POST.get('address_line1') 
        address.address_line2 = request.POST.get('address_line2') 
        address.is_default = bool(request.POST.get('is_default'))
        address.type = request.POST.get('type')
        
        if not address.full_name:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Full name is required'})
            messages.error(request,"Full name is required")
            return redirect('edit_address',id=address.id)
        
        elif not re.match(r'^[A-Za-z ]+$', address.full_name):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Name can only contain letters and spaces'})
            messages.error(request,"Name can only contain letters and spaces")
            return redirect('edit_address',id=address.id)
        
        if len(address.pincode) != 6:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Incorrect pin Code'})
            messages.error(request,"Incorrect pin Code")
            return redirect('edit_address',id=id)
        
        if len(address.phone_number) != 10:
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'Mobile number must be 10 digits'})
            messages.error(request,"no changes made now")
            return redirect('edit_address',id=address.id)
        
        if Address.objects.filter(user=request.user).first():
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
        # Return the new default address id so the frontend can update the UI
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