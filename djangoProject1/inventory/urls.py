from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.search_page, name='search_page'),
    path('search/', views.search_products, name='search_products'),
    path('reserve/', views.reserve_inventory, name='reserve_inventory'),
    path('inventory/<int:product_id>/', views.get_inventory, name='get_inventory'),
] 