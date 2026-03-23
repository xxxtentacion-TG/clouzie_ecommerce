from django.contrib import admin
from django.urls import path
from accounts import views
urlpatterns = [
    path('',views.home,name="home"),
    path('signin',views.signin,name="sigin"),
    path('signup',views.signup,name="signup"),
    path('verify',views.verify,name="verify"),
    path('resend-otp/',views.resend_otp,name="resend_otp"),
    path('forgot-pasword/',views.forgot_password,name="forgot_password"),
    path('forgot-verify/',views.forgot_verify,name="forgot_verify"),
    path('reset-password/',views.rest_password,name="reset_password"),
    path('home/',views.main_home,name="home_main"),
    path('profile/',views.profile,name="profile"),
    path('change-password/',views.change_password,name="change_password"),
    path('edit-profile/',views.edit_profile,name="edit_profile"),
    path('remove-profile/',views.remove_profile,name="remove_profile"),
    path('logout/',views.logout_page,name="logout"),
]
