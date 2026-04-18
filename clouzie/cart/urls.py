from django.urls import path,include
from . import views
urlpatterns = [
    path('',views.cart,name="cart"),
    path('increase/<int:id>/',views.increase,name="increase"),
    path('decrease/<int:id>/',views.decrease,name="decrease"),
    path('remove/<int:id>/',views.remove_item,name="remove"),
]