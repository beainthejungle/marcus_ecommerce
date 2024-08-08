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