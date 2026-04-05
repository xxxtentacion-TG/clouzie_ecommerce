from django.contrib import admin
from django.urls import path
from adminpanel import views

app_name = 'adminpanel'
urlpatterns = [
    path('admin-login',views.admin_login,name="admin-login"),
    path('admin-dashboard',views.admin_dashboard,name="admin-dashboard"),
    path('user-management',views.customers,name="customers"),
    path('user-details/<int:id>',views.customers_details,name="customers_details"),
    path('user-block/<int:id>',views.customer_block,name="customers_block"),
    path('user-unblock/<int:id>',views.customer_unblock,name="customers_unblock"),
    path('admin-logout',views.logout_admin,name="logout-admin"),
]