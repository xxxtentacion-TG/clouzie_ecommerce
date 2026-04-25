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
    path('subcategory/delete/<int:id>',views.delete_subcategory,name="delete_subcategory"),
    path('subcategory/toggle/<int:id>',views.toggle_subcategory,name="subcategory_toggle"),
    
    # PRODUCTS
    path('products',views.products,name="products"),
    path('products/add',views.add_products,name="add_products"),
    path('products/view/<uuid:uuid>',views.view_product,name="view_products"),
    path('products/edit/<uuid:uuid>',views.edit_products,name="edit_products"),
    path('products/delete/<uuid:uuid>',views.delete_products,name="delete_prodcuts"),
    
    
    # VARIANTS
    path('products/<uuid:uuid>/variants/', views.product_variants, name='product-variants'),
    path('update-variant/<int:id>/', views.update_variants, name='update-variants'),
    path('add-variant/', views.add_variant, name='add_variant'),
    path('delete-variant/<int:id>/', views.delete_variants, name='delete-variants'),
    path('toggle-variant/<int:id>/', views.toggle_variant, name='toggle_variant'),
    path('set_default_variant/<int:id>/', views.set_default_variant, name='set_default_variant'),
]