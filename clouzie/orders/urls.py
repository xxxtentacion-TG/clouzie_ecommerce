from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.create_order, name='create_order'),
    path('create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('order-success/<uuid:order_uuid>/', views.order_success, name='order_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('management/', views.order_management, name='order_management'),
    path('details/<uuid:order_uuid>/', views.order_details, name='order_details'),
    path('cancel/<uuid:order_uuid>/', views.cancel_order, name='cancel_order'),
    path('cancel-item/<int:item_id>/', views.cancel_order_item, name='cancel_order_item'),
    path('return/<uuid:order_uuid>/', views.request_return, name='request_return'),
    path('return-item/<int:item_id>/', views.return_order_item, name='return_order_item'),
    path('download_invoice/<uuid:order_uuid>/', views.download_invoice, name='download_invoice'),
]
