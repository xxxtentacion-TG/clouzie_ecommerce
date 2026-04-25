from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.create_order, name='create_order'),
    path('order-success/<uuid:order_uuid>/', views.order_success, name='order_success'),
]