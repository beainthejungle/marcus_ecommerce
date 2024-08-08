from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .cart import Cart
from product.models import ProductPartConstraint, ProductPartVariation


def detail(request):
    return render(request, 'cart/detail.html', {
        'cart': Cart(request)
    })


def clear(request):
    cart = Cart(request)
    cart.clear()

    return redirect('cart:detail')


def add(request, product_part_variation_pk):
    product_part_variation = get_object_or_404(ProductPartVariation, pk=product_part_variation_pk)

    if product_part_variation.is_in_stock:
        cart = Cart(request)
        can_add_part = True
        constraints = ProductPartConstraint.objects.filter(Q(variation_a=product_part_variation) | Q(variation_b=product_part_variation))

        for constraint in constraints:
            if constraint.variation_a == product_part_variation:
                if cart.has_part(constraint.variation_b.part.product_id, constraint.variation_b):
                    can_add_part = False
            elif constraint.variation_b == product_part_variation:
                if cart.has_part(constraint.variation_a.part.product_id, constraint.variation_a):
                    can_add_part = False
        
        if can_add_part:
            cart.add(product_part_variation.part, product_part_variation)
        else:
            messages.warning(request, "These two variations can't be used together")
    else:
        messages.warning(request, "The product is not in stock")

    return redirect('cart:detail')