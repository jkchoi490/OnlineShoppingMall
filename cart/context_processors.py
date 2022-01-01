from .cart import Cart

# 컨텍스트 프로세서 코딩
def cart(request):
    cart = Cart(request)
    context = {
        'cart': cart,
    }
    return context
