from decimal import Decimal, ROUND_DOWN
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse
from django.conf import settings
import razorpay
from .models import Category, Product, Cart, CartItem, Order, OrderItem
from django.http import JsonResponse, HttpResponse, FileResponse
from .models import Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm
from .utils import get_or_create_cart, generate_gst_invoice


# Initialize Razorpay client (Test keys)
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(is_active=True, featured=True)[:8]
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'latest_products': latest_products,
    }
    return render(request, 'store/home.html', context)

def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_active=True)
    
    context = {
        'category': category,
        'products': products,
    }
    return render(request, 'store/category.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, 
        is_active=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if product.stock <= 0:
        messages.error(request, 'Product is out of stock!')
        return redirect('product_detail', slug=product.slug)
    
    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.warning(request, 'Cannot add more items. Stock limit reached!')
            return redirect('cart_view')
    
    messages.success(request, f'{product.name} added to cart!')
    return redirect('cart_view')

def cart_view(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'store/cart.html', context)

def update_cart(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id)
        action = request.POST.get('action')
        
        if action == 'increase':
            if cart_item.quantity < cart_item.product.stock:
                cart_item.quantity += 1
                cart_item.save()
            else:
                return JsonResponse({'status': 'error', 'message': 'Stock limit reached'})
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                return JsonResponse({'status': 'error', 'message': 'Minimum quantity is 1'})
        
        return JsonResponse({
            'status': 'success',
            'quantity': cart_item.quantity,
            'subtotal': float(cart_item.get_subtotal()),
            'cart_total': float(cart_item.cart.get_total())
        })
    
    return JsonResponse({'status': 'error'})

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('cart_view')

def my_orders(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login to view your orders.')
        return redirect('home')

    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'store/my_orders.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from .models import Cart, Order, OrderItem
from .forms import CheckoutForm
from .utils import get_or_create_cart, generate_gst_invoice

def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty!")
        return redirect("home")

    # Calculate totals
    subtotal = sum(item.product.get_selling_price() * item.quantity for item in cart_items)
    gst_amount = sum((item.product.get_selling_price() * item.quantity * item.product.gst_rate)/100 for item in cart_items)
    total_amount = subtotal + gst_amount

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create Order
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.subtotal = subtotal
            order.gst_amount = gst_amount
            order.total_amount = total_amount
            order.payment_status = True  # Direct success
            order.status = 'processing'
            order.save()

            # Create Order Items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.get_selling_price(),
                    hsn_code=item.product.hsn_code,
                    gst_rate=item.product.gst_rate
                )

            # Generate GST Invoice
            generate_gst_invoice(order)

            # Clear cart
            cart.items.all().delete()

            messages.success(request, "Payment successful! Your order has been placed.")
            return redirect("order_success", order_id=order.order_id)

    else:
        form = CheckoutForm(initial={
            "full_name": request.user.get_full_name() if request.user.is_authenticated else "",
            "email": request.user.email if request.user.is_authenticated else ""
        })

    context = {
        "form": form,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "gst_amount": gst_amount,
        "total": total_amount,
    }
    return render(request, "store/checkout.html", context)


def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, "store/order_success.html", {"order": order})


def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    if not order.invoice_generated:
        generate_gst_invoice(order)
    if order.invoice_file:
        from django.http import FileResponse
        response = FileResponse(order.invoice_file.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
        return response
    messages.error(request, "Invoice not found!")
    return redirect("home")


@csrf_exempt
def payment_success(request):
    if request.method != 'POST':
        return redirect('home')

    payment_id = request.POST.get('razorpay_payment_id')
    order_id = request.POST.get('razorpay_order_id')
    signature = request.POST.get('razorpay_signature')

    if not all([payment_id, order_id, signature]):
        messages.error(request, "Payment data missing!")
        return redirect('home')

    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }

    try:
        # Verify Razorpay signature
        razorpay_client.utility.verify_payment_signature(params_dict)

        # Get order
        order = get_object_or_404(Order, razorpay_order_id=order_id)
        order.razorpay_payment_id = payment_id
        order.razorpay_signature = signature
        order.payment_status = True
        order.status = 'processing'
        order.save()

        # Update product stock
        for item in order.items.all():
            product = item.product
            product.stock -= item.quantity
            product.save()

        # Generate GST Invoice
        generate_gst_invoice(order)

        # Clear cart
        cart = get_or_create_cart(request)
        cart.items.all().delete()

        messages.success(request, 'Payment successful! Your order has been placed.')
        return redirect('order_success', order_id=order.order_id)

    except razorpay.errors.SignatureVerificationError:
        messages.error(request, 'Payment verification failed!')
        return redirect('home')
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('home')
    
        from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'store/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered.')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                messages.success(request, 'Account created successfully! Please login.')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match.')
    
    return render(request, 'store/register.html')