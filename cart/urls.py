from django.urls import path
from .views import *

app_name = 'cart'

urlpatterns = [
    # 127.0.0.1:8000/cart
    path('', detail, name='detail'), 

    # 127.0.0.1:8000/cart/add/2
    path('add/<int:product_id>/', add, name='product_add'),

    # 127.0.0.1:8000/cart/remove/2
    path('remove/<int:product_id>/', remove, name='product_remove'),
] 