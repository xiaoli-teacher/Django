from django.contrib import admin
from .models import Product, Inventory

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'created_at', 'updated_at')
    search_fields = ('product__name',)
    list_filter = ('created_at', 'updated_at')
