from django.urls import path
from .views import add_coupon

app_name = 'coupon'

urlpatterns = [
    # 127.0.0.1:8000/coupon --> ?? --> config/urls.py <-- 1차 url
    # 127.0.0.1:8000/coupon/add/
    path('add/', add_coupon, name='add'),
]
