from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('add/<int:item_id>/', views.add_review, name='add_review'),
    path('more/<slug:slug>/', views.load_more_reviews, name='load_more'),
]