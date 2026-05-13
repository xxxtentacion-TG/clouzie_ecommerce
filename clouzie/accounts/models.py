import string
import random as rand_module

# Create your models here.
from django.db import models
# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

def generate_referral_code():
    """Generate a unique 8-character uppercase alphanumeric referral code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(rand_module.choices(chars, k=8))
        if not CustomUser.objects.filter(referral_code=code).exists():
            return code

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)

    is_blocked = models.BooleanField(default=False)
    is_admin_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Referral system ──────────────────────────────────────
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referrals',
    )
    referral_reward_given = models.BooleanField(default=False)
    # ─────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):

        if not self.referral_code:
            self.referral_code = generate_referral_code()

        if not self.username:

            base_username = self.email.split("@")[0]

            username = base_username

            counter = 1

            while CustomUser.objects.filter(username=username).exists():

                username = f"{base_username}{counter}"

                counter += 1

            self.username = username

        super().save(*args, **kwargs)

class Meta:
    db_table = 'users'
    
    class meta:
        db_table = 'users'
    
    class meta:
        db_table = 'users'
        
        
class Otp(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()
    
    def is_expired(self):
        return timezone.now() > self.expired_at

    def save(self, *args, **kwargs):
        if not self.expired_at:
            self.expired_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
        
class Address(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=100)
    
    type = models.CharField(max_length=20,choices=[
        ('home','Home'),
        ('work','Work'),
        ('other','Other'),
    ])
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    