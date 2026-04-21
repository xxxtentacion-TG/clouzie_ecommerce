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
            if user_obj.is_blocked:
                return render(request,"accounts/login_page.html",{"error":"Account is Blocked"})
            
            if user_obj.is_admin_user:
                return render(request,"accounts/login_page.html",{"error":"Admin not Allowed"})
            if user is not None:
                login(request,user)
                request.session['user_id'] = user.id
                request.session.set_expiry(1209600)
                messages.success(request, "Logged in successfully",extra_tags='login')
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
        spassword = request.POST.get('password')
        confirmpassword = request.POST.get('confirmPassword', '').strip()
        
        if (
            not susername and
            not semail and
            not spassword and
            not confirmpassword
        ):
            messages.error(request,'please fill all details first.')
            return redirect('signup')
        
        
        if not valid_password(spassword):
            messages.error(request,'Password must be 6+ chars with letters & numbers')
            return redirect('signup')
        
        if not valid_email(semail):
            messages.error(request,'Enter a valid email address')
            return redirect('signup')
        
        if spassword != confirmpassword:
            messages.error(request,'Passwords does not match')
            return redirect('signup')
        checkuser = CustomUser.objects.filter(email=semail).first()
        
        if CustomUser.objects.filter(username=susername).exists():
            messages.error(request,'Username is existing choose another one')
            return redirect('signup')
        
        if checkuser:
            if checkuser.is_active:
                messages.error(request,'Email already registred. Please login.')
                return redirect('signup')
                
            else:
                otp_code = str(random.randint(100000, 999999))
                expiry_time = timezone.now() + timedelta(minutes=5)
                request.session['checkuser_id'] = checkuser.id
                Otp.objects.filter(user_id=checkuser.id).delete()
                
                Otp.objects.create(
                user_id=checkuser.id,              
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
                to=[checkuser.email],
                )

                email.attach_alternative(html_content, "text/html")
                email.send()
                request.session['verify_user_id'] = checkuser.id
                return redirect('verify')
        
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
        user = CustomUser.objects.filter(id=user_id).first()
        otp_obj = Otp.objects.filter(user_id=user_id).last()
        
        if not otp_obj:
            messages.error(request,'Please enter the Valid Otp')
            return redirect('verify')
        
        if len(Otp_input) != 6:
            messages.error(request,'Please enter the complete 6-digit verification code.')
            return redirect('verify')
        
        
        if Otp_input != otp_obj.code:
            messages.error(request,"The verification code you entered is incorrect. Please try again.")
            return redirect('verify')
        
        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request,'Your verification code has expired. Please request a new one to continue.')
            return redirect('verify')
        
        user.is_active = True
        user.save()
        Otp.objects.filter(user_id=user_id).delete()
        request.session.pop('user_id',None)
        messages.success(request,"account created succuessfully")
        return redirect('sigin')
    return render(request,"accounts/verify.html")

@never_cache  
def resend_otp(request):
    verify_user = request.session.get('verify_user_id')
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
        femail = request.POST.get('email')
        request.session['reset_email'] = femail
        user = get_object_or_404(CustomUser,email=femail)
        request.session['forgot_user_id'] = user.id
        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)
        
        
        if not femail:
            return render(request, "accounts/forgot_password.html",{"error":"Email is required"})
        try:
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
        otp_obj = Otp.objects.filter(user_id=user_id).first()
        if otp_obj.code != Otp_input:
            return render(request,'accounts/verify.html',{"error":"The verification code you entered is incorrect. Please try again."})
        
        if len(Otp_input) != 6:
            return render(request,"accounts/verify.html",{"error":"Please enter the complete 6-digit verification code."})
        
        if not Otp_input:
            render(request,"accounts/verify.html",{"error":"Enter the Otp first myre"})
            
        if otp_obj.is_expired():
            otp_obj.delete()
            return render(request,"accounts/verify.html",{"error":"Your verification code has expired. Please request a new one to continue."})
        
        return redirect("reset_password")
        
    return render(request,"accounts/forgot_verify.html")

def forgot_resend_otp(request):
    
    if request.method == "POST":

        email = request.session.get("reset_email")
        if not email:
            return redirect("forgot_verify")
        user = CustomUser.objects.get(email=email)
        Otp.objects.filter(user_id=user.id).delete()
        otp_code = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(minutes=5)
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
    return render(request,'accounts/main_page.html',{"new_arrivals":new_arrivals})
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
        username = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        image = request.FILES.get('profile_image')
        if image is not None:
            if user.profile_photo:
                user.profile_photo.delete(save=False)
                
        if user.username == username and user.phone_number == phone and user.email == email and user.profile_photo == image:
            messages.error(request,"no chanage made now ")
            return redirect('edit_profile')
        
        if username != user.username:
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request,'username already existing')
                return redirect('edit_profile')
            
        if not valid_email(email):
            return render(request,"accounts/edit_profile.html",{"error":"Enter a valid email address"})
        if email and email != user.email:
            if CustomUser.objects.filter(email=email).exists():
                return render(request,"accounts/edit_profile.html",{"error":"Email already registered"})
            if Otp.objects.filter(user_id=user.id).exists():
                Otp.objects.filter(user_id=user.id).delete()
                
            request.session['email_user_id'] = user.id
            request.session['email_id'] = email
            otp_code = str(random.randint(100000, 999999))
            expiry_time = timezone.now() + timedelta(minutes=5)
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
            return redirect('email_verify')
        
        user.username = username
        user.phone_number = phone
        if image:
            user.profile_photo = image
            
        user.save()
        messages.success(request,"profile updated succuessfully")
        return redirect('edit_profile')
    return render(request,"accounts/edit_profile.html",{"user":user_details})
@login_required
@never_cache
def email_verify(request):
    user_id = request.session.get('email_user_id')
    user = get_object_or_404(CustomUser,id=user_id)
    
    if request.method == "POST":
        Otp_input = ''.join([request.POST.get(f'v{i}','') for i in range(1,7)])
        otp_obj = Otp.objects.get(user_id=user_id)
        if otp_obj.code != Otp_input:
            return render(request,'accounts/email_verify.html',{"error":"The verification code you entered is incorrect. Please try again."})
        
        if len(Otp_input) != 6:
            return render(request,"accounts/email_verify.html",{"error":"Please enter the complete 6-digit verification code."})
         
        if otp_obj.is_expired():
            otp_obj.delete()
            return render(request,"accounts/email_verify.html",{"error":"Your verification code has expired. Please request a new one to continue."})
        Otp.objects.filter(user_id=user_id).delete()
        user.email = request.session.get('email_id')
        user.save()
        request.session.pop('email_user_id',None)
        request.session.pop('email_id',None)
        return redirect('profile')
        
        
    return render(request,"accounts/email_verify.html")
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

        for field in fields:
            if not request.POST.get(field):
                messages.error(request,"fill the address first")
                return render(request,"accounts/add_address.html",{"full_name":full_name,"phone_number":phone_number,"address_line1":address_line1,"state":state,"pincode":pincode,"city":city,"address_line2":address_line2})
        

        if not full_name:
            messages.error(request,"Full name is required")
            return redirect('add_address')
        
        elif not re.match(r'^[A-Za-z ]+$', full_name):
            messages.error(request,"Name can only contain letters and spaces")
            return redirect('add_address')

        if len(pincode) != 6:
            messages.error(request,"Incorrect pin Code")
            return redirect('add_address')
        
        if len(phone_number) != 10:
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
        messages.success(request,"Address added successfully")
        return redirect('address')
    return render(request,"accounts/add_address.html")
@login_required
@never_cache
def edit_address(request,id):
    address = get_object_or_404(Address,id=id,user=request.user)
    addressess = Address.objects.filter(id=id,user=request.user)
    if request.method == "POST":
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
            messages.error(request,"Full name is required")
            return redirect('edit_address',id=address.id)
        
        elif not re.match(r'^[A-Za-z ]+$', address.full_name):
            messages.error(request,"Name can only contain letters and spaces")
            return redirect('edit_address',id=address.id)
        
        if len(address.pincode) != 6:
            messages.error(request,"Incorrect pin Code")
            return redirect('edit_address',id=id)
        
        if len(address.phone_number) != 10:
            messages.error(request,"no changes made now")
            return redirect('edit_address',id=address.id)
        
        if Address.objects.filter(user=request.user).first():
            address.is_default = True
            
        if is_default:
            Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)
            address.is_default = True
            
        address.save()
        messages.success(request,"address updated successfully")
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

def temp(request):
    return render(request,"accounts/temp.html")

def custom_404(request, exception):
    return render(request, 'base/404.html', status=404)