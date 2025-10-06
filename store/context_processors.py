from .models import Cart

def cart_count(request):
    cart_items_count = 0
    
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()
        else:
            cart = None
    
    if cart:
        cart_items_count = cart.get_total_items()
    
    return {'cart_items_count': cart_items_count}