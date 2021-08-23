from django import forms 
from .models import Order 

# 주문서 view 작성을 위해 필요한 폼(form)
# 사용자로부터 주문 정보를 받아오는데 필요한 form
# form은 프런트에서 받아올 정보를 노출
# 사용자로부터 넘어온 데이터를 기본적으로 검증(validation)
class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order 
        fields = [
            'first_name',
            'last_name',
            'email',
            'address',
            'postal_code',
            'city',
        ]