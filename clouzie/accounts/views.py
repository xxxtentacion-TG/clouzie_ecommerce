from django.shortcuts import render,redirect
from django.http import HttpResponse
from .models import CustomUser,Otp
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
# Create your views here.

def home(request):
    return render(request, 'accounts/home.html')

def signin(request):
    if request.method == 'POST':
        lemail = request.POST.get('email')
        lpassword = request.POST.get('password')
        
        user = authenticate(request,email=lemail,password=lpassword)
        if user is not None:
            login(request,user)
            return redirect('home_main')
        
        return render(request,"accounts/login_page.html",{"error":"Incorrect login details.","email":lemail,"password":lpassword})
        
        
    return render(request,"accounts/login_page.html")

def signup(request):
    
    if request.method == 'POST':
        susername = request.POST.get('username')
        semail = request.POST.get('email')
        spassword = request.POST.get('password')
        confirmpassword = request.POST.get('confirmPassword', '').strip()
        
        
        if not valid_password(spassword):
            return render(request,"accounts/signup.html",{"error":"Password must be 6+ chars with letters & numbers","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword})
        
        if not valid_email(semail):
            return render(request,"accounts/signup.html",{"error":"Enter a valid email address","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword})
        
        if spassword != confirmpassword:
            return render(request,"accounts/signup.html",{"error": "Passwords do not match.","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword})
        
        if CustomUser.objects.filter(email=semail).exists():
            return render(request,"accounts/signup.html",{"error": "Email already registered.","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword})
        
        if CustomUser.objects.filter(username=susername).exists():
            return render(request,"accounts/signup.html",{"error":"username existing","username":susername,"password":spassword,"email":semail,"password":spassword,"confirmpassword":confirmpassword})
        user = CustomUser.objects.create_user(
            username=susername,
            email=semail,
            password=spassword,
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
        
        return redirect('verify')
        
    return render(request,"accounts/signup.html")

def valid_username(username):
    return re.fullmatch(r'^[A-Za-z0-9]{3,20}$', username)

def valid_email(email):
    return re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def valid_password(password):
    return re.fullmatch(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$', password)


def verify(request):
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
        
def resend_otp(request):
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
            request.session['user_id'] = user.id
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

def forgot_verify(request):
    if request.method == 'POST':
        Otp_input = ''.join([request.POST.get(f'v{i}','') for i in range(1,7)])
        user_id = request.session.get('user_id')
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

def rest_password(request):
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
        return redirect('sigin')
    return render(request,"accounts/reset_password.html")

def main_home(request):
    return render(request,'accounts/main_page.html')
        
        

        