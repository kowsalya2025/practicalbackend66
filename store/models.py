from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='products/')
    stock = models.IntegerField(default=0)
    hsn_code = models.CharField(max_length=20, default='00000000')
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_selling_price(self):
        if self.discounted_price:
            return self.discounted_price
        return self.price
    
    def get_discount_percentage(self):
        if self.discounted_price:
            discount = ((self.price - self.discounted_price) / self.price) * 100
            return round(discount)
        return 0
    
    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_total(self):
        total = sum(item.get_subtotal() for item in self.items.all())
        return total
    
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    def __str__(self):
        return f"Cart {self.id} - {self.user or self.session_key}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def get_subtotal(self):
        return self.product.get_selling_price() * self.quantity
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_id = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_method = models.CharField(max_length=50, default='razorpay')
    razorpay_order_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=500, blank=True, null=True)
    payment_status = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invoice_generated = models.BooleanField(default=False)
    invoice_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order {self.order_id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    hsn_code = models.CharField(max_length=20)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    def get_subtotal(self):
        return self.price * self.quantity
    
    def get_gst_amount(self):
        return (self.get_subtotal() * self.gst_rate) / 100
    
    def get_total(self):
        return self.get_subtotal() + self.get_gst_amount()
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
