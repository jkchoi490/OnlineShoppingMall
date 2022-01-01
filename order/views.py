from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.http import HttpResponse 
from django.template.loader import render_to_string

from .models import *
from cart.cart import Cart
from .forms import OrderCreateForm
import weasyprint

# 주문서를 입력받기 위해 작성하는 view
# 함수형 뷰의 첫번째 파라미터는 request로 설정
# 요청 메서드 request를 들고 있어야 어떤 형태(GET, POST 등)로 요청했고
# 어떤 파라미터와 헤더를 사용했는지 확인하거나 활용할 수 있음
# 
# 
# ajax 기능을 이용하여 주문서를 처리
#   -> 주문서 입력을 위한 폼 출력을 제외하고
#      자바스크립트가 작성하지 않는 환경에서만 작동
def order_create(request):
    cart = Cart(request)
    
    # POST 형태로 접근한 경우
    if request.method == 'POST':
        
        # 입력받은 정보를 후처리
        # GET 방식으로 접근한 경우에는 빈 form을 생성하지만,
        # POST 방식으로 접근한 경우는 request.POST를 이용해
        # 전달받은 정보를 변수로 받아서 내용을 처리함
        form = OrderCreateForm(request.POST)
        
        # form이 멀쩡하다면, 후처리 수행
        if form.is_valid():
            
            # 모델 form 이기 때문에 save 하면, order 객체 생성
            order = form.save()
            
            # 쿠폰이 있다면, 쿠폰 관련 후처리 수행
            if cart.coupon:
                order.coupon = cart.coupon
                
                # 할인쿠폰 로직에서 제품가격이 
                # 쿠폰보다 적을 경우 쿠폰 적용
                order.discount = cart.get_discount_total()
                
                # 쿠폰이 있다면 무조건 쿠폰 할인 적용하는 로직
                # order.discount = cart.coupon.amount
                
                order.save()
            
            # 카트에 쿠폰이 있든 없든, 주문 정보 처리
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
            
            # 주문이 들어 갔으면, 장바구니 비우기
            cart.clear()

            context = {
                'cart': cart,
                'order': order,
            }

            return render(request, 'order/created.html', context)

    # GET 방식으로 접근했을 경우
    else:
        # 주문자 정보를 입력받는 페이지
        form = OrderCreateForm() # 빈 FORM 생성
        
        # cart 정보와 form 정보를 html로 전달
        context2 ={
            'cart': cart,
            'form':form,
        }
    
    # POST 방식에서는 데이터 후처리를 해서 return 하지만,
    # 중간에 에러 (form 양식 미준수 등) 발생 시 초기 html로 return 
    return render(request, 'order/create.html', context2)


# 주문정보 입력 --> 결재완료 --> 주문완료를 화면에 표시하기 위한 view
# JS 동작하지 않는 환경에서도 주문은 가능해야한다.
# 열악한 환경인 경우(구 브라우저, JS안되는 경우)
# 위에서 만든 return render(request, 'order/created.html', context)로 렌더링
# JS가 되는 경우 아래의 order_complete 작동
def order_complete(request):
    order_id = request.GET.get('order_id')
    order = Order.objects.get(id=order_id)
    # order = get_object_or_404(Order, id=order_id)
    context = {
        'order': order
    }
    return render(request, 'order/created.html', context)


from django.views.generic.base import View
from django.http import JsonResponse 

# 1st ajax view (클래스형 뷰)
# 1. 사용자가 입력한 주문 정보를 서버에 저장
# 2. 장바구니 비우기
# 3. 장바구니에 있던 OrderItem 객체 저장
class OrderCreateAjaxView(View):
    def post(self, request, *args, **kwargs):
        
        # 사용자 인증 여부 확인
        if not request.user.is_authenticated:
            return JsonResponse(
                {'authenticated': False},
                status=403
            )
        
        # 장바구니, 주문정보 저장
        cart = Cart(request)
        form = OrderCreateForm(request.POST)

        if form.is_valid():
            
            # 주문정보 저장
            order =form.save(commit=False) 
            
            # 쿠폰이 있다면 주문정보 업데이트
            if cart.coupon:
                order.coupon = cart.coupon 
                order.discount = cart.coupon.amount  
            
            # 쿠폰 정보를 포함하여 저장
            order = form.save()
            
            # 장바구니에 있던 OrderItem 객체 저장
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
            
            # 장바구니 비우기
            cart.clear()

            data = {
                'order_id': order.id,
            }

            return JsonResponse(data)
        
        else:
            return JsonResponse({}, status=401)

# 2nd ajax view: OrderCheckoutAjaxView (클래스형 뷰)
# 1. 실제 결재를 하기 전에 Order Transaction 객체 생성하는 역할
# 2. OrderTransaction 객체 생성과정에서 생성한 merchant_order_id를 
#    반환 받아서 다음 절차에 사용
class OrderCheckoutAjaxView(View):
    
    def post(self, request, *args, **kwargs):
        
        # 로그인 여부 판단
        # Mixin을 활용하는 방안도 가능함
        if not request.user.is_authenticated:
            return JsonResponse({'authenticated': False}, status=403)
        
        order_id = request.POST.get('order_id') # get: 사전 자료형에서 사용
        order = Order.objects.get(id=order_id)
        amount = request.POST.get('amount')

        try:
            # order 앱 Model의 OrderTransactionManager에서 
            # OrderTransaction 생성하고
            # transaction.merchant_order_id를 리턴 받음
            merchant_order_id = OrderTransaction.objects.create_new(
                order=order,
                amount=amount,
            )
        except:
            merchant_order_id = None
        
        if merchant_order_id != None:
            data = {
                'works': True,
                'merchant_id': merchant_order_id,
            }
            return JsonResponse(data)
        else:
            return JsonResponse({}, status=401)

# 3rd ajax view (클래스형 뷰)
# 1. 실제 결재가 끝난 뒤에 결제를 검증하는 View --> 모든 코드가 후처리 관련 내용임
# 2. 결재 검증까지 마치고 나면 order_complete View를 호출하여
#    주문이 완료되었음을 표시하고 전체 결재 절차를 종료한다.
class OrderImpAjaxView(View):
    
    def post(self, request, *args, **kwargs):
        
        # 로그인 여부 확인 
        # Mixin 사용이 가능하지만, 다만 json response 안됨
        if not request.user.is_authenticated:
            return JsonResponse({'authenticated': False}, status=403)

        order_id = request.POST.get('order_id')
        
        # order id를 갖는 order 객체 생성
        order = Order.objects.get(id=order_id)
        
        # ajax를 통해 보낸 내용을 다시 받아옴
        merchant_id = request.POST.get('merchant_id')
        imp_id = request.POST.get('imp_id')
        amount = request.POST.get('amount')

        try:
            trans = OrderTransaction.objects.get(
                order=order,
                merchant_order_id=merchant_id,
                amount=amount,
            )
        except:
            trans = None
        
        # 만약 제대로 된 정보가 있다면
        # 해당 정보로 업데이트 함
        if  trans is not None:
            trans.transaction_id = imp_id 
            
            # trans.success를 사용하기 위해서는
            # order 모델에 다음과 같은 필드가 있어야 함 <-- 우리 코드에는 없음
            # --> success = models.BooleanField(default=False) 
            # 따라서 아래 코드는 생략함

            # trans.success = True # 생략
            
            trans.save() # 결재 완료 --> 거래 정보 저장
            order.paid = True # 대금이 지불되었으므로(trans.save()) True 변경
            order.save()  # 주문 정보 저장
            # 여기까지 결재 및 주문이 완료된 상황임
            
            data = {
                'works': True
            }
            
            # 최종적으로 결재 및 주문 완료 정보를 JsonResponse를 이용하여 전달
            return JsonResponse(data)
        
        else:
            # 결재 및 주문이 제대로 되지 않으면 401에러 반환
            return JsonResponse({}, status=401)

# 관리자 커스텀 페이지 처리를 위한 뷰
# Order 모델을 임포트 해야 함
# 현재는 wild import (from .models import *)로 
# 임포트 된 상태
# 관리자만 사용할 수 있도록 staff_member_required 적용
#   - staff_member_required 임포트 해야함
@staff_member_required
def admin_order_detail(request, order_id):
    # 모델에서 order_id를 가지고 있으면 진행
    # 그렇지 못할 경우 HTTP 404 페이지로 이동
    order = get_object_or_404(Order, id=order_id)
    context = {
        'order': order,
    }
    return render(request, 'order/admin/detail.html', context)
    
# PDF 변환을 위해 HttpResponse를 임포트하여
# 뷰에서 처리해야 함
#   - from django.http import HttpResponse
@staff_member_required
def admin_order_pdf(request, order_id):
    # 모델에서 order_id를 가지고 있으면 진행
    # 그렇지 못할 경우 HTTP 404 페이지로 이동
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string(
        'order/admin/pdf.html',
        {'order': order}
    )
    # response에 담겨진 html 형식을  pdf로 변환
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename=order_{}.pdf'.format(order_id)
    
    # pdf 출력을 위한 css 파일은 로컬에 있어야 함
    # response라는 파일에다 weasyprint에서 변환한 내용을 적용
    # settings.STATICFILES_DIRS[0] -> Local 파일을 불러오는 명령
    #   static/css/pdf.css 파일을 만들어 놓아야 함
    weasyprint.HTML(string=html).write_pdf(
        response, 
        stylesheets=[weasyprint.CSS(settings.STATICFILES_DIRS[0]+'/css/pdf.css')]
    )
    
    # pdf 파일을 리턴함
    return response
