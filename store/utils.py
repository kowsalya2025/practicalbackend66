import os
from io import BytesIO
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.files.base import ContentFile
from .models import Order, Cart


def generate_gst_invoice(order):
    """
    Generates a GST invoice PDF for a given order and saves it to order.invoice_file.
    """
    try:
        template_path = 'store/invoice.html'
        template = get_template(template_path)

        order_items = order.items.all()
        subtotal = sum(item.price * item.quantity for item in order_items)
        gst_amount = sum((item.price * item.quantity * item.gst_rate) / 100 for item in order_items)
        grand_total = subtotal + gst_amount

        context = {
            'order': order,
            'order_items': order_items,
            'subtotal': subtotal,
            'gst_amount': gst_amount,
            'grand_total': grand_total,
        }

        html = template.render(context)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

        if not pdf.err:
            file_name = f"invoice_{order.order_id}.pdf"
            order.invoice_file.save(file_name, ContentFile(result.getvalue()))
            order.invoice_generated = True
            order.save()
            return True
        else:
            print("Error generating PDF:", pdf.err)
            return False
    except Exception as e:
        print("Exception in generate_gst_invoice:", str(e))
        return False


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


