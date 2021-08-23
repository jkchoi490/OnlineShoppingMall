from django.urls import path 
from .views import *

# 여기는 order 앱 url 구성하는 페이지
# 2차 url 연결하면,
# 루트에 1차 url도 연결해야 함 (config 폴더의 urls.py 연결)

app_name = 'orders'

urlpatterns = [
    path('create/', order_create, name='order_create'),
    path('create_ajax', OrderCreateAjaxView.as_view(), name='order_create_ajax'),
    path('checkout/', OrderCheckoutAjaxView.as_view(), name='order_checkout'),
    path('validation/', OrderImpAjaxView.as_view(), name='order_validation'),
    path('complete/', order_complete, name='order_complete'),
        # 커스텀 관리자 페이지 임시 추가
    path('order_detail/<int:order_id>/', admin_order_detail, name='admin_order_detail'),
    path('order_pdf/<int:order_id>/', admin_order_pdf, name='admin_order_pdf'),
]
