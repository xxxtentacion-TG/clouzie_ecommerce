from django.urls import path
from . import views

app_name = 'checkout'

urlpatterns = [
    path('', views.checkout_view, name='checkout'),
    path('remove-coupon/', views.remove_coupon, name='remove-coupon'),
    path("apply-coupon/", views.apply_coupon, name="apply_coupon"),
]