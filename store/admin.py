from django.contrib import admin
from .models import Category, Product, Cart, CartItem, Order, OrderItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discounted_price', 'stock', 'is_active', 'featured']
    list_filter = ['category', 'is_active', 'featured']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'featured', 'stock']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'created_at', 'get_total_items']
    list_filter = ['created_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'get_subtotal']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'hsn_code', 'gst_rate']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'full_name', 'email', 'total_amount', 'payment_status', 'status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_id', 'email', 'phone', 'full_name']
    readonly_fields = ['order_id', 'razorpay_order_id', 'razorpay_payment_id', 'created_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_id', 'status', 'created_at')
        }),
        ('Customer Info', {
            'fields': ('user', 'full_name', 'email', 'phone', 'address', 'city', 'state', 'pincode')
        }),
        ('Payment Info', {
            'fields': ('subtotal', 'gst_amount', 'total_amount', 'payment_method', 
                      'razorpay_order_id', 'razorpay_payment_id', 'payment_status')
        }),
        ('Invoice', {
            'fields': ('invoice_generated', 'invoice_file')
        }),
    )
