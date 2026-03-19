from django.contrib import admin
from django.urls import path
from accounts import views
urlpatterns = [
    path('',views.home,name="home"),
    path('signin',views.signin,name="sigin"),
    path('signup',views.signup,name="signup"),
    path('verify',views.verify,name="verify"),
    path('resend-otp/',views.resend_otp,name="resend_otp"),
]
