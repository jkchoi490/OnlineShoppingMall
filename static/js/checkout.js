$(function() {
    
    // js 변수 설정
    var IMP=window.IMP;
    
    // 아임포트 대시보드-시스템-내정보-가맹점식별코드에서 확인, 
    // 경고 REST API secret이 노출되지 않도록 항상 주의해야함
    IMP.init('imp06463859');
    
    // order-form 상태가 submit on (제출하기 클릭) 상태이면 function 실행시킴
    $('.order-form').on('submit', function(e) {

        // order-form에서 가격을 찾아서 콤마(,)를 제거
        var amount = parseFloat($('.order-form input[name="amount"]').val().replace(',',''));
        
        // 결재 종류(카드, 이체, 기타 등)를 확인하여 해당 결재창을 보여주도록 하는 코드
        var type=$('.order-form input[name="type"]:checked').val();
        
        // 결재하기 버튼 누름 --> 주문생성 - 결재 = 결재정보 업데이트
        // AjaxCreateOrder는 아래에서 별도로 만들 함수
        var order_id = AjaxCreateOrder(e);
        if(order_id==false) {
            alert('주문 생성 실패\n다시 시도해주세요.');
            return false; 
            // return false --> 폼이 동작하지 않도록 함, 
            // return true --> submit이 완료되어 페이지가 변환 되는 등 변화 발생
        }

        var merchant_id = AjaxStoreTransaction(e, order_id, amount, type);

        // 결재 정보가 만들어졌다면 아임포트로 실제 결재 시도
        // 아임포트 결재 매뉴얼 확인: https://bit.ly/3njJjQy
        // 아임포트에서 요구하는 대로 작성해야 함**
        if(merchant_id!=='') {
           
            // 아임포트에서 받을 정보(결재 요청 정보) -> 아임포트에 보내줄 내용
    
                IMP.request_pay({pg : 'html5_inicis',
                pay_method : 'card',
                
                //merchant_uid : 'merchant_' + new Date().getTime(),
                merchant_uid:merchant_id,
                
                // 매 제품마다 해당 제품 내용이 들어가도록 바꿀수 있음
                // 현재는 하나의 제품 이름으로 지정함
                name:'E-Shop product',
                buyer_name:$('input[name="first_name"]').val()+" "+$('input[name="last_name"]').val(),
                buyer_email:$('input[name="email"]').val(),
                amount:amount
            }, function(rsp) {
                
                // 결재가 성공한 경우
                if(rsp.success) {
                    
                    // 결제 완료후 보여줄 메시지
                    var msg = '결제가 완료되었습니다.';
                    msg += '고유 ID : ' + rsp.imp_uid;
                    msg += '상점 거래ID : ' + rsp.merchant_uid;
                    msg += '결제 금액 : ' + rsp.paid_amount;
                    msg += '카드 승인번호 : ' + rsp.apply_num;
                    // 필요한 문자열을 추가로 설정할 수 있음
                    
                    // 결재 검증을 위한 Ajax 함수, 아래에 내용을 구현해 줘야 함 --> 검증 및 환불 가능
                    // rsp.imp_uid (결재 고유번호) --> 요게 있어야 나중에 환불 처리 가능하다
                    // 검증 과정으로 넘김 --> 아임포트에서 넘겨받은 정보와 내 서버에 저장된 정보를 비교
                    ImpTransaction(e, order_id, rsp.merchant_uid, rsp.imp_uid, rsp.paid_amount);
                } 
                
                // 결재에 실패한 경우
                else {
                    var msg = '결제에 실패하였습니다.';
                    msg += '에러내용 : '+ rsp.error_msg;
                    
                    // 브라우저에 console 객체가 있는 경우 실행
                    // console 없는 브라우저는 아무일도 일어나지 않음
                    console.log(msg); 
                    
                }
            });
        }
        // Ajax로 모든 결재를 진행했기 때문에 
        // 결재가 완료 되었지만 창이 submit 되면 안됨 --> 2중 결재 위험 등
        return false;
    });
});

// $('.order-form').on('submit', function(e) {...}가 실행되었던
// 이벤트(event) e를 그대로 들고 와서 활용하는 AjaxCreateOrder 함수
function AjaxCreateOrder(e) {
    
    // Form이 submit 되는 것을 방지하기
    // 위 함수에서 return false가 있어서 어차피 작동 안함
    // 안저한 작동을 위해 추가
    e.preventDefault();

    var order_id = '';

    // Ajax 처리 수행
    var request = $.ajax({
        
        // order 생성하는 뷰를 POST로 호출
        method:'POST', 
        
        // 템플릿에 준비된 url --> order/templates/order/create.html
        //      {% block script %}
        //          <script type="text/javascript">
        //              csrf_token = '{{ csrf_token }}';
        //              order_create_url = '{% url "orders:order_create_ajax" %}';
        //              :
        // 
        // urls 설정에 표시 --> order/urls.py
        //      app_name = 'orders'
        //          urlpatterns = [
        //          path('create_ajax', OrderCreateAjaxView.as_view(), name='order_create_ajax'),
        url:order_create_url, 
        
        // 비동기 수행 --> 결재 과정이 꼬일 수 있어서 false 처리
        // (기본적으로는 jQuery에서 Ajax는 비동기 방식(async)으로 작동)
        async:false, 
        
        // .serialize() --> 데이터 가져와서 순서대로 처리
        // order-form에 들어있는 값들을 일일이 다음과 같이 만들지 않아도 됨
        // 사전(dict) 형태로 자동으로 만들어주고, 요청시 아래와 같이 만들어 url 생성
        // fname=값&femail=값&sex=값&job=값 ...
        data:$('.order-form').serialize()  
    });

    // 위에서 호출한 request에 대한 응답이 온 경우
    // 만약 정상적으로 데이터가 있다면
    request.done(function(data) {
        
        // data.order_id는 어디에서 올까?
        //      order/views.py/
        //          class OrderCreateAjaxView(View)의 리턴값
        if(data.order_id) {
            order_id = data.order_id;
        }
    });

    // 만약 데이터에 문제가 발생할 경우
    // jqXHR은 관례적 이름, 다른 이름도 무방함(예: response 등)
    request.fail(function(jqXHR, textStatus) {
        if(jqXHR.status == 404) {
            alert("페이지가 존재하지 않습니다.");
        } else if(jqXHR.status==403) {
            alert("로그인 해주세요.");
        } else {
            alert("문제가 발생했습니다.\n다시 시도해주세요.");
        }
    });

    return order_id;
}

// $('.order-form').on('submit', function(e) {...}가 실행되었던
// 이벤트(event) e를 그대로 들고 와서 활용하는 AjaxStoreTransaction 함수
// AjaxCreateOrder 함수와 중복되는 부분은 코멘트 생략
function AjaxStoreTransaction(e, order_id, amount, type) {
    // Form이 submit 되는 것을 방지하기
    // 위 함수에서 return false가 있어서 어차피 작동 안함
    // 안저한 작동을 위해 추가
    e.preventDefault();
    var merchant_id = '';
    var request = $.ajax({
        method:'POST',
        
        // 템플릿에 준비된 url --> order/templates/order/create.html
        //      {% block script %}
        //          <script type="text/javascript">
        //              order_checkout_url = '{% url "orders:order_checkout" %}';
        //              :
        // 
        // urls 설정에 표시 --> order/urls.py
        //      app_name = 'orders'
        //          urlpatterns = [
        //              path('checkout/', OrderCheckoutAjaxView.as_view(), name='order_checkout'),    
        //              :
        url: order_checkout_url,
        async:false,
        
        // form을 serialize 할 것이 없으므로, 직접 보낼 내용을 사전으로 작성해 준다
        data: {
            order_id:order_id,
            amount:amount,
            type:type,
            csrfmiddlewaretoken:csrf_token,
        }
    });
    request.done(function(data) {
        if(data.works) {
            merchant_id = data.merchant_id;
        }
    });
    request.fail(function(jqXHR, textStatus) {
        if(jqXHR.status == 404) {
            alert("페이지가 존재하지 않습니다.");
        } else if(jqXHR.status==403) {
            alert("로그인 해주세요.");
        } else {
            alert("문제가 발생했습니다.\n다시 시도해주세요.");
        }
    });
    return merchant_id;
}

// 마지막 ajax 함수~~~ 프런트 코드(javaScript 등)는 쉽게 조작이 가능하다
// 거래 검증 기능: 아임포트 측에 요청을 보내서 값을 받음 
//    --> 우리 서버에 저장된 정보와 비교
function ImpTransaction(e, order_id, merchant_id, imp_id, amount) {
    e.preventDefault();
    
    // ajax 코드 요청
    var request = $.ajax({
        method:"POST",
        url:order_validation_url,
        async:false,
        data:{
            order_id:order_id,
            merchant_id:merchant_id,
            imp_id:imp_id,
            amount:amount,
            csrfmiddlewaretoken:csrf_token
        }
    });
    request.done(function(data) {
        
        // 제대로 작동했다면 url 변경
        // order/templates/order/create.html -->
        //      order_complete_url = '{% url "orders:order_complete" %}';
        // order/urls.py --> 
        //      path('complete/', order_complete, name='order_complete')
        // order/view.py --> 
        //      def order_complete(request):
        //      order_id = request.GET.get('order_id')
        //      order = Order.objects.get(id=order_id)
        // # order = get_object_or_404(Order, id=order_id)
        //      context = {
        //          'order': order
        //      }
        //      return render(request, 'order/created.html', context)
        if(data.works) {
            $(location).attr('href', location.origin+order_complete_url+'?order_id='+order_id)
        }
    });

    // 중복 코드, 복붙해서 활용
    request.fail(function(jqXHR, textStatus) {
        if(jqXHR.status == 404) {
            alert("페이지가 존재하지 않습니다.");
        } else if(jqXHR.status==403) {
            alert("로그인 해주세요.");
        } else {
            alert("문제가 발생했습니다.\n다시 시도해주세요.");
        }
    });
}