from django.shortcuts import get_object_or_404, render

from .models import Product


def detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    return render(request, 'product/detail.html', {
        'product': product
    })