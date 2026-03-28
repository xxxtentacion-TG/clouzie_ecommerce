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
# Create your views here.
def home(request):
    if request.user.is_authenticated:
        return redirect('home_main')
    
    return render(request, 'accounts/home.html')
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
            
            if user is not None:
                login(request,user)
                request.session['user_id'] = user.id
                request.session.set_expiry(1209600)
                return redirect('home_main')
            return render(request,"accounts/login_page.html",{"error":"invalid email or password"})
        
        except CustomUser.DoesNotExist:
            return render(request,"accounts/login_page.html",{"error":"invalid email or password"})
          
    return render(request,"accounts/login_page.html")

@never_cache
def signup(request):
    
    if request.method == 'POST':
        susername = request.POST.get('username')
        semail = request.POST.get('email')
        phone = request.POST.get('phone')
        spassword = request.POST.get('password')
        confirmpassword = request.POST.get('confirmPassword', '').strip()
        
        if not valid_password(spassword):
            return render(request,"accounts/signup.html",{"error":"Password must be 6+ chars with letters & numbers","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword,"phone":phone})
        
        if not valid_email(semail):
            return render(request,"accounts/signup.html",{"error":"Enter a valid email address","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword,"phone":phone})
        
        if spassword != confirmpassword:
            return render(request,"accounts/signup.html",{"error": "Passwords do not match.","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword,"phone":phone})
        
        if CustomUser.objects.filter(email=semail).exists():
            return render(request,"accounts/signup.html",{"error": "Email already registered.","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword,"phone":phone})
        
        user = CustomUser.objects.create_user(
            username=susername,
            email=semail,
            password=spassword,
            phone_number=phone,
            is_active=False
        )
        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)
        request.session['user_id'] = user.id
        Otp.objects.filter(user_id=user.id).delete()
        
        Otp.objects.create(
        user_id=user.id,              
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
        request.session['verify_user_id'] = user.id
        return redirect('verify')
        
    return render(request,"accounts/signup.html")

def valid_username(username):
    return re.fullmatch(r'^[A-Za-z0-9]{3,20}$', username)

def valid_email(email):
    return re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def valid_password(password):
    return re.fullmatch(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$', password)

@never_cache
def verify(request):
    user_id = request.session.get('verify_user_id')
    if not user_id:
        return redirect('sigin')
    
    if request.method == "POST":
        Otp_input = ''.join([request.POST.get(f'v{i}','') for i in range(1,7)]) 
        
        user_id = request.session.get('user_id')
        user = CustomUser.objects.get(id=user_id)
        otp_obj = Otp.objects.filter(user_id=user_id).last()
        
        if not otp_obj:
            return render(request,'accounts/verify.html',{"error":"Your verification code has expired. Please request a new one to continue."})
        
        if len(Otp_input) != 6:
            return render(request,"accounts/verify.html",{"error":"Please enter the complete 6-digit verification code."})
        
        if Otp_input != otp_obj.code:
            return render(request,"accounts/verify.html",{"error":"The verification code you entered is incorrect. Please try again."})
        
        if otp_obj.is_expired():
            otp_obj.delete()
            return render(request,"accounts/verify.html",{"error":"Your verification code has expired. Please request a new one to continue."})
        
        user.is_active = True
        user.save()
        Otp.objects.filter(user_id=user_id).delete()
        request.session.pop('user_id',None)
        return redirect('sigin')
    return render(request,"accounts/verify.html")

@never_cache  
def resend_otp(request):
    verify_user = request.session.get('verify_user_id')
    if not verify_user:
        return redirect('sigin')
    
    user_id = request.session.get('user_id')
    Otp.objects.filter(user_id=user_id).delete()
    if not user_id:
        return JsonResponse({'error':'Session expired'},status=400)
    
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
    return JsonResponse({'success':True})
@never_cache 
def forgot_password(request):
    if request.method == 'POST':
        femail = request.POST.get('email')
        request.session['reset_email'] = femail
        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)
        
        if not femail:
            return render(request, "accounts/forgot_password.html",{"error":"Email is required"})
        try:
            user = CustomUser.objects.get(email=femail)
            request.session['forgot_user_id'] = user.id
            Otp.objects.filter(user_id=user.id).delete()
            Otp.objects.create(
                code=otp_code,
                expired_at=expiry_time,
                user_id=user.id
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
            return redirect('forgot_verify')
        except CustomUser.DoesNotExist:
            return render(request,"accounts/forgot_password.html",{"error":"Please enter a valid email address."})
        
    return render(request,"accounts/forgot_password.html")

@never_cache
def forgot_verify(request):
    forgot_user = request.session.get('forgot_user_id')
    if not forgot_user:
        return redirect('sigin')
        
    if request.method == 'POST':
        
        Otp_input = ''.join([request.POST.get(f'v{i}','') for i in range(1,7)])
        user_id = request.session.get('forgot_user_id')
        otp_obj = Otp.objects.get(user_id=user_id)
        if otp_obj.code != Otp_input:
            return render(request,'accounts/forgot_verify.html',{"error":"The verification code you entered is incorrect. Please try again."})
        
        if len(Otp_input) != 6:
            return render(request,"accounts/verify.html",{"error":"Please enter the complete 6-digit verification code."})
         
        if otp_obj.is_expired():
            otp_obj.delete()
            return render(request,"accounts/verify.html",{"error":"Your verification code has expired. Please request a new one to continue."})
        
        return redirect("reset_password")
        
    return render(request,"accounts/forgot_verify.html")

@never_cache
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
        if rpassword != cpassword:
            return render(request,"accounts/reset_password.html",{"error":"The passwords you entered do not match. Please try again."})
        
        if not valid_password(rpassword):
            return render(request,"accounts/reset_password.html",{"error":"Password must be 6+ chars with letters & numbers"})
        if not valid_password(cpassword):
            return render(request,"accounts/reset_password.html",{"error":"Password must be 6+ chars with letters & numbers"})
        user.set_password(rpassword)
        user.save()
        request.session.pop('forgot_user_id',None)
        return redirect('sigin')
    return render(request,"accounts/reset_password.html")
@login_required
def main_home(request):
    return render(request,'accounts/main_page.html')
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

        if not user.check_password(old_password):
            return render(request,"accounts/change_password.html",{'error':"Old passowrd incorrect Try again.","old_password":old_password,"new_password":new_password,"cnfrm_password":cnfrm_password})
        
        if new_password != cnfrm_password:
            return render(request,"accounts/change_password.html",{"error":"Passwords do not match","old_password":old_password,"new_password":new_password,"cnfrm_password":cnfrm_password})
        if not valid_password(new_password):
            return render(request,"accounts/change_password.html",{"error":"Password must be 6+ chars with letters & numbers","old_password":old_password,"new_password":new_password,"cnfrm_password":cnfrm_password})
        if not valid_password(cnfrm_password):
            return render(request,"accounts/change_password.html",{"error":"Password must be 6+ chars with letters & numbers","old_password":old_password,"new_password":new_password,"cnfrm_password":cnfrm_password})
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request,user)
        return redirect('profile')
    
    return render(request,'accounts/change_password.html') 


@login_required
@never_cache
def edit_profile(request):
    user = request.user
    user_details = CustomUser.objects.get(id=user.id)
    if request.method == 'POST':
        username = request.POST.get('name')
        phone = request.POST.get('phone')
        image = request.FILES.get('profile_image')
        if image is not None:
            if user.profile_photo:
                user.profile_photo.delete(save=False)
        
        user.username = username
        user.phone = phone
        if image:
            user.profile_photo = image
            
        user.save()
        return redirect('profile')
    return render(request,"accounts/edit_profile.html",{"user":user_details})


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
    return redirect('home')

def dummy(request):
    return HttpResponse("hello world")   
@login_required
@never_cache
def adress(request):
    address = Address.objects.filter(user=request.user).order_by('-is_default')
    return render(request,"accounts/address.html",{"address":address})
@login_required
@never_cache
def add_address(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        pincode = request.POST.get('pincode')
        city = request.POST.get('city') 
        state = request.POST.get('state') 
        address_line1 = request.POST.get('address_line1') 
        address_line2 = request.POST.get('address_line2') 
        is_default = bool(request.POST.get('is_default'))
        address_type = request.POST.get('type')
        
        if is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
            
        fields = [
        "full_name", "phone_number", "address_line1",
        "city", "state", "pincode"
        ]

        for field in fields:
            if not request.POST.get(field):
                return redirect("/add-address/?error=1")
        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone_number,
            pincode=pincode,
            city=city,
            state=state,
            address_line1=address_line1,
            address_line2=address_line2,
            is_default = is_default,
            type = address_type   
        )
        return redirect('/address/?success=1')
    return render(request,"accounts/add_address.html")
@login_required
@never_cache
def edit_address(request,id):
    address = get_object_or_404(Address,id=id,user=request.user)
    if request.method == "POST":
        is_default = bool(request.POST.get('is_default'))
        address.full_name = request.POST.get('full_name')
        address.phone_number = request.POST.get('phone_number')
        address.pincode = request.POST.get('pincode')
        address.city = request.POST.get('city') 
        address.state = request.POST.get('state') 
        address.address_line1 = request.POST.get('address_line1') 
        address.address_line2 = request.POST.get('address_line2') 
        address.is_default = bool(request.POST.get('is_default'))
        address.address_type = request.POST.get('type')
        
        if is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
        address.save()
        return redirect('address')
    return render(request,"accounts/edit_address.html",{"address":address})
@login_required
@never_cache
def delete_address(request,id):
    address = get_object_or_404(Address,id=id)
    if address.is_default:
        new = Address.objects.filter(user=request.user).exclude(id=id).first()
        if new:
            new.is_default = True
            new.save()
        
    address.delete()
    return redirect('address')