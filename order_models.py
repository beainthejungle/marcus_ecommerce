from django.db import models

from product.models import ProductPart, ProductPartVariation


class Order(models.Model):
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    CANCELLED = 'cancelled'

    CHOICES_STATUS = (
        (PROCESSING, 'Processing'),
        (SHIPPED, 'Shipped'),
        (CANCELLED, 'Cancelled'),
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100, blank=True, null=True)
    zipcode = models.CharField(max_length=15)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    email = models.EmailField()
    status = models.CharField(max_length=25, choices=CHOICES_STATUS, default=PROCESSING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def get_total_price(self):
        return sum(item.item_total_price * item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_part = models.ForeignKey(ProductPart, on_delete=models.CASCADE)
    product_part_variation = models.ForeignKey(ProductPartVariation, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    item_price = models.IntegerField()
    item_extra_price = models.IntegerField(blank=True, null=True)
    item_total_price = models.IntegerField(blank=True, null=True)