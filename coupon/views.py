from django.shortcuts import render
from django.shortcuts import redirect
from .forms import AddCouponForm
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Coupon

@require_POST
def add_coupon(request):
    # 현재시간 확인
    now = timezone.now()

    form = AddCouponForm(request.POST)

    # 쿠폰 유효성성 검사
    if form.is_valid():
        code = form.cleaned_data['code']

        try:
            # 만약 유효기간 내 쿠폰이라면
            coupon = Coupon.objects.get(
                # 쿠폰번호 일치
                code__iexact=code,

                # 시작 시간보다 커야됨
                use_from__lte=now,

                # 사용기한은 현재(now)보다 커야 됨
                use_to__gte=now,

                # 쿠폰이 유효한지 (액티브 상태인 쿠폰인가?)
                active=True 
            )
            request.session['coupon_id'] = coupon.id

        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None

    return redirect('cart:detail')