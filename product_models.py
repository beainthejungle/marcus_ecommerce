from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Categories'

    def __str__(self):
        return f'{self.name}'


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}'

    def get_display_price(self):
        return self.price / 100
    

class ProductPart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}'


class ProductPartVariation(models.Model):
    part = models.ForeignKey(ProductPart, related_name='variations', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.IntegerField()
    is_in_stock = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} - {self.part.name}'

    def get_display_price(self):
        return self.price / 100


class PriceDependent(models.Model):
    """
    use cases:
    for example if the price on a product part like paint is dependent on the size/type of frame
    """
    base_variation = models.ForeignKey(ProductPartVariation, related_name='base_variation', on_delete=models.CASCADE)
    dependent_variation = models.ForeignKey(ProductPartVariation, related_name='dependent_variation', on_delete=models.CASCADE)
    adjusted_price = models.IntegerField()

    def __str__(self):
        return f'{self.base_variation.name} - {self.dependent_variation.name}'


class ProductPartConstraint(models.Model):
    """
    use cases:
    for example if two product part variations shouldn't be used together
    """
    variation_a = models.ForeignKey(ProductPartVariation, related_name='contraint_a', on_delete=models.CASCADE)
    variation_b = models.ForeignKey(ProductPartVariation, related_name='contraint_b', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.variation_a.name} - {self.variation_b.name}'