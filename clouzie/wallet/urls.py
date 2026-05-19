from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    path('', views.wallet_management, name='wallet'),
    path('create-topup/', views.create_wallet_topup, name='create_topup'),
    path('verify-payment/', views.verify_wallet_payment, name='verify_wallet_payment'),
]
