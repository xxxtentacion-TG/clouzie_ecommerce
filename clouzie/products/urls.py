from django.urls import path
from . import views

urlpatterns = [
    path('mens', views.products_list,name='product_list'),
]