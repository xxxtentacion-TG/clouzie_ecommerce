from django.urls import path
from . import views

urlpatterns = [
    path('mens', views.products_list,name='product_list'),
    path('clear-toast/', views.clear_toast, name='clear_toast'),
    path('<slug:slug>/', views.product_details,name='product_details'),
    path('add-to-cart/<slug:slug>', views.add_to_cart,name='add_to_cart'), 
]