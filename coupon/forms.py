from django import forms 

class AddCouponForm(forms.Form):
    code = forms.CharField(label='쿠폰번호를 입력하세요')