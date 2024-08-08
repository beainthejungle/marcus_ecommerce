# Marcus E-commerce Website

The project is built with / based on Django. Django uses an ORM, so there is no raw SQL.

I have split the project into multiple Django apps to keep the structure as clean and clear as possible, as well as making it easy to scale. I will go through each of the the Django apps here, and explain what I have done, why, etc.

First of all, all Django apps usually exists of a set of database models, views, templates and a few more files. A Django app should be easy to understand from the name, and should be easy to explain.

## Product

The product app is the app which will be used to show a product, categories, database tables, etc.

I have created on model for the categories. Right now, Marcus is only selling bicycles, but since this app now have a categories model, it should be easy to add more later.

### Product model

The next model in the models file is the Product model. This has a name, a description field, a relation to the category and a field for the price. The reason I chose to use IntegerField and not a DecimalField for the price is that usually payment gateways like Stripe expects to get the price in cents. To make this field easy to use, I have created a method "get_display_price" that divides the price by 100 to display it like dollars or euros.

An example of a product is a bicycle (Usually we have different types of bicycles like racing, mtb, bmx, etc.)

```python
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
```

### Product Part model 

Next, we have the product part model. This is for example the "chain", "frame type", "frame finish", etc. It's very simple and only have a reference to the product it belongs to, and a name.

```python
class ProductPart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}'
```

### Product part variation model

For each of the product parts, there are usually multiple variations like "matte", "shiny", etc.

This model is a little bit more complicated than the product part.

First, we have a reference to the product part this variation belongs to. I have set a "related_name" which makes it really easy to get all the variations that a part has.

Next, we have a name, description and price field. At the end, we have a boolean field which makes it easy to set a variation of a product part in or out of stock.

```python
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
```

### Price dependant model

Some parts has a variable price based on a part it is connected to. For example, it's cheaper to paint a small frame than a large.

There are basically two fields that connects two variations, and a field for the adjusted price (For example, add 1500 cents for a specific frame type / finish combination).

Usually for connecting two models like this, I like to use a ManyToManyField, but since I need the price field here, I needed a separate model.

```python
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
```

### Product part constraint

This is similar to the price dependant model, except this is made for making it impossible to use two variations together.

```python
class ProductPartConstraint(models.Model):
    """
    use cases:
    for example if two product part variations shouldn't be used together
    """
    variation_a = models.ForeignKey(ProductPartVariation, related_name='contraint_a', on_delete=models.CASCADE)
    variation_b = models.ForeignKey(ProductPartVariation, related_name='contraint_b', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.variation_a.name} - {self.variation_b.name}'
```

### The product page

Ideally, I would like to use the product view for nothing more than getting the product from the database and rendering it a view. This way, I can separate the business logic behind adding it to the cart, checking availability, etc into the cart app.

A Django view would therefor be very simple like this:

```python
def detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    return render(request, 'product/detail.html', {
        'product': product
    })
```

For the UI, I would show a picture of a bike, with the description, etc, on the left side of the screen.

On the right side, I would have a sidebar where the user can customize the bicycle. If all bicycles has the same base parts, I would list them out in the sidebar as small boxes (With icon, select variation name, current price, and a button for replacing that specific part).

When a user clicks the "replace" button, I would show a modal where all available variations are showing. The prices, information, etc should be automatically updated through an API.

To calculate the price for each of the product parts, total price, etc, I would have a method in the API that collects all the data and temporarily store it in a session. In this function, I would also check if the product variation is in stock, if it's compatible with the other parts you have selected and if the price is dependant on any of the other parts. (In the next part of this document, I will append an example of this).

Also if the user has selected the Fat bike wheels, and then go to the "rim color" product type, the "red" color should be greyed out or similar to indicate that you can't click on it. Plus, if you hover the mouse of the "red", a little tip should pop up.

When the user clicks the "add to cart" button, I would use the same functionality as we just used for calculation, but instead actually appending it to the cart.

So far, this is something I would like to just store in the session for the user. If this was supposed to be stored in a database, we would also need a way of connecting this to a specific user and similar.

## Cart

The cart app is a very important of the e-commerce website, at least the way I think it should be structured.

Here, we'll have a class called Cart. This will be used to keep track of all the information the user has selected in a session. It will be used for updating the cart, clearing it, etc.

I think it's a good practice to have all of the add to cart functionality inside this app. Some of the code will be in the Cart class and some of the code in the view.

The code in the Cart class will be used for storing it in the session, checking if you already have it in the session, etc. 

```python
from django.conf import settings

from product.models import PriceDependent


class Cart(object):
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.setdefault(settings.CART_SESSION_ID, {})


    def __iter__(self):
        """
        iterate over the values in the cart and convert them to "products"
        """
        
        variant_ids = []

        for product in self.cart.values():
            for part in product['parts']:
                variant_ids.append(part['variant'])

        for product in self.cart.values():
            total_price = 0

            for part in product['parts']:
                part['total_price'] = part['price'] * part['quantity']

                # Check price dependant
                for dependant in PriceDependent.objects.filter(base_variation=part['id']):
                    if dependant.dependent_variation.id in variant_ids:
                        part['extra_price'] = dependant.adjusted_price
                        part['total_price'] += dependant.adjusted_price

                total_price += part['total_price']

            product['total_price'] = total_price

            yield product
    

    def add(self, product_part, product_part_variation, quantity=1):
        """
        add or update product in cart
        """

        product_part_id_key = str(product_part.id)
        product_id_key = str(product_part.product.id)

        if product_id_key not in self.cart:
            self.cart[product_id_key] = {
                'id': product_id_key,
                'total_price': quantity * product_part_variation.price,
                'parts': []
            }

            self.add_part(product_id_key, product_part_id_key, product_part_variation, quantity)
        else:
            if product_part_id_key in [part['id'] for part in self.cart[product_id_key]['parts']]:
                self.update_part(product_id_key, product_part_id_key, product_part_variation, quantity)
            else:
                self.add_part(product_id_key, product_part_id_key, product_part_variation, quantity)

        self.save()


    def add_part(self, product_id_key, product_part_id_key, product_part_variation, quantity):
        """
        adds the part (not product) to the cart (list of parts for a product)
        """
        self.cart[product_id_key]['parts'].append({
            'id': product_part_id_key,
            'price': quantity * product_part_variation.price,
            'extra_price': 0,
            'quantity': quantity,
            'variant': product_part_variation.id,
            'total_price': quantity * product_part_variation.price
        })


    def update_part(self, product_id_key, product_part_id_key, product_part_variation, quantity):
        """
        updates the part (not product) in the cart (list of parts for a product)
        """
        for part in self.cart[product_id_key]['parts']:
            if part['id'] == product_part_id_key:
                part['extra_price'] = 0
                part['quantity'] = quantity
                part['variant'] = product_part_variation.id
                part['price'] = quantity * product_part_variation.price
                part['total_price'] = quantity * product_part_variation.price

    
    def has_part(self, product_id, product_part_variation):
        """
        checks if a specific part is in cart
        """
        if len(self.cart) > 0:
            for part in self.cart[str(product_id)]['parts']:
                if part['id'] == str(product_part_variation.part_id):
                    return True
        
        return False
    

    def get_total_cost(self):
        """
        returns the total price (in cents) for the cart
        """
        return sum(float(item['total_price']) for item in self)
    

    def get_total_cost_display(self):
        """
        returns the total price (in cents) for the cart for printing purpose
        """
        return self.get_total_cost() / 100


    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True
    

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.session.modified = True
```

The view it self will take care of checking if the product is in stock, if there are any constraints, etc.


```python
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
```

## Order

The order app is used for keeping track of orders after a checkout has been completed. When the user interacts with the cart, nothing should be persisted in the database before the user actually checks out. And that's when these order models is created.

### The order model

First, I defined some constants for keeping track of the status. Some people choose to do this with integers instead of strings, but it's easier to understand "processing" than 1.

Most of the fields here are just fields for keeping track of the information about the user. But there is a status field which uses the constants, and fields for keeping track of when the order was created and modified.

```python
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
```

### Order item model

This model is used to keep track of all the products / parts in an order. 

This model has a reference to the order it belongs to, which product part and which variation. I defaulted the quantity to 1, because we usually just have one part/variation of all parts of a bicycle.

Next, I have a item_price which is used for the "base price" of a variation (For example 1500 cents for the paint of the frame). item_extra_price is used to keep track of any extra costs if the frame is bigger or similar. item_total_price is used for combining price and extra_price.

```python
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_part = models.ForeignKey(ProductPart, on_delete=models.CASCADE)
    product_part_variation = models.ForeignKey(ProductPartVariation, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    item_price = models.IntegerField()
    item_extra_price = models.IntegerField(blank=True, null=True)
    item_total_price = models.IntegerField(blank=True, null=True)
```

## The admin interface

To create a new product, the only information Marcus needs to fill out is the name of the product, select a category and write a description. Maybe add a few images as well. 

Maybe all products doesn't need parts/variations, so the cart and product page also would need to take this into consideration. And if the product needs parts, the product should not be showing on the website part if not everything is ready.

Each of the products should have a detail page in the admin interface. In this UI, there should be boxes (similar to the ones in the sidebar on the product page) and a button for adding a new part. To add a new choice to a part, the user should click the box and be presented with a modal. In this modal, all of the other variations/choices should be rendered. In the form for the product part, a field for selecting constraints should also be rendered. To make it easy to work with for the user, it should be some sort of search field (ideally a live search) used to find other parts/variations. A button for saving the for should be located clearly, and when this is clicked, the information will be updated in the database.

To change the price for a specific part/variation, Marcus should follow the same routine as when he is adding new parts/variations. Click on a part to see the modal with all variations, and then select a variation which should toggle/show a form with all the fields connected to it filled out. Here, it should be easy to change the price or set up a dependency on a different part. 
