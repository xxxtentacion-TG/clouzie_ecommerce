from django.contrib import admin
from django.urls import path
from . import views

app_name = 'adminpanel'
urlpatterns = [
    #AUTH
    path('admin-login',views.admin_login,name="admin-login"),
    path('admin-logout',views.logout_admin,name="logout-admin"),
    # DASHBOARD
    path('admin-dashboard',views.admin_dashboard,name="admin-dashboard"),
    
    # USERES
    path('user-management',views.users,name="customers"),
    path('user-details/<int:id>',views.users_details,name="customers_details"),
    path('user-block/<int:id>',views.customer_block,name="customers_block"),
    path('user-unblock/<int:id>',views.customer_unblock,name="customers_unblock"),
    
    # CATEGORIES
    path('categories',views.categories,name="category"),
    path('categories/add',views.add_categories,name="add_category"),
    path('categories/edit/<int:id>',views.edit_categories,name="edit_category"),
    path('categories/toggle/<int:id>',views.toggle_status,name="category_toggle"),
    path('categories/delete/<int:id>/',views.delete_category,name="delete_category"),
    path('subcategory',views.subcategory,name="subcategory"),
    path('subcategory/add',views.add_subcategory,name="add_subcategory"),
    path('subcategory/edit/<int:id>',views.edit_subcategory,name="edit_subcategory"),
]