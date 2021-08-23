from .cart import Cart

# 컨텍스트 프로세서 코딩
# 교재 p. 354 (코드 06-84)
def cart(request):
    cart = Cart(request)
    context = {
        'cart': cart,
    }
    return context
