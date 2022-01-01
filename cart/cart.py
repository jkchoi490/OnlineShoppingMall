from decimal import Decimal
from django.conf import settings 
from shop.models import Product
from coupon.models import Coupon

class Cart(object):
    # Dunder (Double Underscore) method Overwirte
    
    # 장바구니 세션 생성시 초기화 작업
    def __init__(self, request): # Typo error: reqest -> request
        self.session = request.session
        cart = self.session.get(settings.CART_ID)
        if not cart: # Missing the keyword 'not'
            cart = self.session[settings.CART_ID] = {}
        self.cart = cart

        self.coupon_id = self.session.get('coupon_id')

    # len(cart객체) --> xx
    # 장바구니 객체에 담긴 갯수
    def __len__(self):
        return sum([ item['quantity'] for item in self.cart.values()])
    
    # 반복문 실행 시 장바구니에 담긴 상품을 순회
    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        
        for product in products:
            self.cart[str(product.id)]['product'] = product
        
        for item in self.cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity'] # Typo: itme -> item
            yield item
    
    # 장바구니에 상품 추가하기
    def add(self, product, quantity=1, is_update=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] =  {'quantity': 0, 'price': str(product.price)}
        
        if is_update:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        
        self.save()

    # 장바구니 저장하기(담기)
    def save(self):
        self.session[settings.CART_ID] = self.cart 
        self.session.modified = True

    # 장바구니에서 특정 상품 삭제
    #def remove(self): # Missing argument typo: product
    #    product_id = str(product_id) # Typo: product_id --> product.id
    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del(self.cart[product_id])
            self.save()

    # 장바구니 비우기
    def clear(self):
        self.session[settings.CART_ID] = {}
        self.session.modified = True
        self.session['coupon_id'] = None

    # 장바구니에 담긴 상품의 전체 가격
    def get_product_total(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())


    # For coupon processing
    # property 데코레이터 참고 블로그: https://www.daleseo.com/python-property/ 
    #   함수가 attribute처럼 동작하도록 함
    @property
    def coupon(self):
        if self.coupon_id:
            return Coupon.objects.get(id=self.coupon_id)
        else:
            return None 
    
    def get_discount_total(self):
        # 쿠폰을 가지고 있는 경우
        # 쿠폰 할인 금액보다 제품가격이 
        # 큰 경우에만 쿠폰 할인액 적용 
        # * 배송비 계산 제외
        if self.coupon:
            if self.get_product_total() >= self.coupon.amount:
                return self.coupon.amount
        
        # 쿠폰 할인이 없으면 0을 리턴
        return Decimal(0)
    
    def get_total_price(self):
        final_price = self.get_product_total() - self.get_discount_total()
        return final_price
    
    