from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from coupon.models import Coupon
from shop.models import Product 

class Order(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    postal_code = models.CharField(max_length=50)
    city = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)

    coupon = models.ForeignKey(
        Coupon, 
        on_delete=models.PROTECT, 
        related_name='order_coupon', 
        null=True, 
        blank=True
    )

    discount = models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100000),
        ]
    )
    
    class Meta:
        ordering = ['-created']
    
    # 객체 자체를 출력하거나 삭제할때 사용
    # 파이썬 기본 문법
    def __str__(self):
        #return f'Order {self.id}' # f 문법, 파이썬 3.6 이후 버전 적용
        return 'Order {}'.format(self.id)
    
    # 결재 완료 통보를 받으면, 
    # 우리가 가지고 있는 정보와 비교할 경우 사용
    def get_total_product(self):
        return sum(item.get_item_price() for item in self.items.all())
        # items의 비밀: 아래 선언한 OrderItem에서 foreignkey의  
        # 'related_name' 변수에 할당된 이름이 items임
        #    |--> 나를 참조하는 모델에서 나를 어떻게 콜 할지를 정하는 변수

    def get_total_price(self):
        total_product = self.get_total_product()
        # 현 시스템은 배송비는 고려하지 않음
        return total_product - self.discount

# 주문에 포함된 제품 정보를 담기 위해 만드는 모델
# 제품 가격의 경우 현시점 가격으로 저장(변동 가능하므로)
class OrderItem(models.Model):
    # 어떤 주문에 연결된 제품인지 
    # ForeignKey로 연결
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, # 주문이 삭제되면, 주문 아이템도 삭제
        related_name='items'
        # 연결된 Order 클래스 입장에서 OrderItem 클래스를 
        # 호출할 때 사용하게 될 이름
        # 우리 예제: Order 클래스 get_total_product에서 OrderItem 호출
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT, # 주문이 걸려 있으면 주문제품 삭제 불가
        related_name='order_products',
        # 연결된 Product 클래스 입장에서 OrderItem 클래스를 
        # 호출할 때 사용하게 될 이름
    )
    
    # 실제 쇼핑몰에서는 가격이 수시로 변경 (세일, 할인, 등등)
    #       제품 내용은 그대로 놔두고 일부 성능만 올라간 경우 
    #       페이지를 유지하고 싶을 경우 
    # 매번 제품 가격이 달라짐
    # 고객이 환불 요청 시 주문했던 당시의 가격으로 환불해야함
    # 제품 가격이 변할때마다 항상 가격 정보를 저장하는 것이 바람직

    price =models.DecimalField(
        max_digits=10,
        decimal_places=2, # 소수점 설정
    )
    
    quantity = models.PositiveIntegerField(default=1)

    # 객체 자체를 출력하거나 삭제할때 사용
    # 파이썬 기본 문법
    def __str__(self):
        # 다양한 문자열 처리 문법 가능 - 개인 입맛대로 활용
        #return f'{self.id}'
        #return str(self.id)
        return '{}'.format(self.id)
        
    # 주문에 대한 아이템 가격을 알아내기 위한 메소드
    # 제품단가 * 수량
    def get_item_price(self):
        return self.price * self.quantity

# 주문 결재 정보를 보관하고 관리하는 클래스
# model.objects() --> manager 역할
# 데이터베이스 작업을 할 경우에는 Manager 클래스를
# 상속받아서 사용할 것을 권장
# 이 경우 DB transaction이 발생했을 경우 
# 해당 order 정보를 갖게 해주는 클래스

import hashlib 
from .iamport import payment_prepare, find_transaction
# 주문을 눌렀을때 결재 정보를 DB에 입력하고 결재안됨 상태로 표시
# 결재가 완료되면 해당 결재 상태를 결재완료 상태로 변환

# 장고 모델의 기본 매니저는 objects임
# 추가적인 데이터 작업을 할 경우에는
# models.Manager 클래스를 상속받아 커스텀 매니저를 관례적으로 만듬
# OrderTransactionManager: 새로 거래를 만들었을때 주문 정보를 하나 갖도록 함
class OrderTransactionManager(models.Manager): # Manager 클래스 상속받음

    # 이 매니저는 결재 정보를 생성할 때 해시 함수를 이용해
    # merchant_order_id를 생성함 --> 아임포트로 보낼 고유한 주문번호
    
    def create_new(self, order, amount, success=None, transaction_status=None):
        '''
        order: 어떤 주문에 대한 transaction을 생성할 
                것인지에 대한 정보, Order 객체라고 생각하면 됨
        amount: 주문 금액
        success: 결재 완료 여부
        transaction_status: transaction 상태, 처음 만들 경우 정보 없음
        success/transaction_status가 None 상태라는 의미는
        최초 거래는 주문정보와 금액만 가지고 생성 가능하다는 의미
        '''
        # 주문이 없을 경우 에러 발생 --> 무조건 에러 뿜어야 함
        if not order:
            raise ValueError('주문 정보 오류')
        
        # 고유한 주문번호를 생성하기 위한 작업
        # 주문 번호가 중복 될 경우 시스템 에러 발생 가능
        # 암호방식은 sha1 이외의 다른 방식을 사용해도 무방함 (심지어 암호화를 안해도 됨)
        order_hash = hashlib.sha1(str(order.id).encode('utf-8')).hexdigest()
        email_hash = str(order.email).split('@')[0] # 이메일 아이디 사용
        
        # Unique한 주문번호를 생성하기 위함
        # iamport로 우리회사의 고유 주문번호를 보내기 위해 사용
        # 앞 10 글자만 따오기
        final_hash = hashlib.sha1((order_hash + email_hash).encode('utf-8')).hexdigest()[:10]

        
        # Python 문자열 표현 방법 3가지
        merchant_order_id = '%s' % (final_hash)
        # merchant_order_id = '{}'.format(final_hash)
        # merchant_order_id = f'{final_hash}'

        # 아이엠포트에 주문(주문번호, 금액 전달)을 사전 통보하여 
        # 우리회사가 요청하는 주문 아이디와 금액으로 iamport에게 
        # 준비하도록 요청함
        payment_prepare(merchant_order_id, amount)
        
        # 상속받은 models.Manager에서 이미 가지고 있는 
        # models.Manager를 상속 받았으므로 model이 있을 것임
        # model을 사용하여 transaction 생성하고 주문정보 연결
        
        # model:
        # 아래에 정의된 OrderTransaction 클래스에서
        # 나의 모델 메니저를 지정하여 사용
        # 즉, self.model은 내 매니저가 누구다라고 
        # 지정한 객체에 접근하는 방식임
        transaction = self.model(
            order=order,
            merchant_order_id=merchant_order_id,
            amount=amount,
        )

        # 만약 transaction 정보가 있다면
        if success is not None:
            transaction.success = success
            transaction.transaction_status = transaction_status

        # transaction 저장
        try: 
            transaction.save()
        except Exception as e:
            print('save error', e)
        
        return transaction.merchant_order_id 
    
    # ORM을 이용하여 호출가능한 메서드
    # object.XXX 형태로 호출할 수 있는 메서드   
    # 주문번호를 이용하여 결재 정보 확인
    def get_transaction(self, merchant_order_id):
        # 아엠포트에서 unique 값으로 관리하는 아이디를 보내주면
        # 결과를 찾아서 보내줌
        result = find_transaction(merchant_order_id)
        if result['status'] == 'paid':
            return result 
        else:
            return None

# 주문에 따른 결재 정보를 담고(저장하고) 있는 클래스
# 정산에 문제가 생긴 경우, 환불할 경우 등에 필요한 정보
class OrderTransaction(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE, # 주문 정보가 없어지면 거래 정보도 삭제
    )
    
    # 상점 아이디
    merchant_order_id = models.CharField(
        max_length=120,
        null=True,
        blank=True,
    )

    # 아이엠포트에서 Primary Key 처럼 관리
    # 우리 회사에서 요청하는 거래 정보 아이디라고 생각하면 편함
    # 거래 취소, 확인 등에 필요한 정보
    transaction_id = models.CharField(
        max_length=120,
        null=True,
        blank=True,
    )

    # 거래 금액
    #amount = models.PositiveIntegerField(default=0) 
    # 해외인 경우 소소점 필요, 국내인 경우 금액에 소수점은 불필요
    amount = models.DecimalField(max_digits=10, decimal_places=2) 
    
    # 제약글자 (max_length) 수는 아이엠포트 경우임
    # 만약 우리 회사가 특정 PG(결재대행사)와 계약을 하게되면
    # 그쪽에서 요청하는 길이로 맞춰주면 됨
    transaction_status = models.CharField(
        max_length=220, 
        null=True, 
        blank=True
    )

    # 거래 유형
    type = models.CharField(max_length=120, blank=True)
    
    # 거래 시간 정보
    created = models.DateTimeField(auto_now_add=True, auto_now=False)

    # 나를 관리해주는 매니저를 연결해 주는 것
    # --> 위에서 정의한 OrderTransactionManager가 self.model을 통해
    # 현재 내 모델에 접근하여 다양한 매니저 작업을 수행하게 해준다
    # s 가 붙는 것에 유의할 것
    objects = OrderTransactionManager()

    def __str__(self):
        return str(self.order.id)
    
    class Meta:
        ordering = ['-created']

# 시그널(signal)을 이용한 결재 검증 함수
# 시그널(signal): 특정 기능이 수행되었음을 
#   장고 애플리케이션 전체에 알리는 용도
# 시그널을 이용해 특정 기능 수행 이전 또는 이후에 
#   별도의 로직(logic) 추가 가능
def order_payment_validation(sender, instance, created, *args, **kwargs):
    
    if instance.transaction_id:

        # 주문 정보를 이용하여 아이엠포트 측에서 동일한 정보를 다시 가져옴
        # 비교할 정보: 아이엠포트의 transaction, order_id, amount, local_transaction
        
        iamport_transaction = OrderTransaction.objects.get_transaction(
            merchant_order_id=instance.merchant_order_id
        )
        merchant_order_id = iamport_transaction['merchant_order_id']
        imp_id = iamport_transaction['imp_id']
        
        # 거래 전후 가격 비교(해키여부 확인)
        amount = iamport_transaction['amount']

        local_transaction = OrderTransaction.objects.filter(
            merchant_order_id=merchant_order_id,
            transaction_id=imp_id,
            amount=amount
        ).exists()

        if not iamport_transaction or not local_transaction:
            raise ValueError('비정상 거래입니다.')

# 결재 정보가 생성된 이후에 호출할 함수를 연결
# signal을 이용한 결재 검증
# signal이란 특정 기능이 수행되었음을 장고 애플리케이션 전체에 알리는 기능
# signal을 이용해 특정 기능 전후에 별도의 로직을 추가할 수 있음
#   방법 1. 동기방법: 특정 작업이 끝날때까지 계속 지켜보다가 끝나면 알려줌
#   방법 2. 비동기방법: 다른 일을 하다가 일을 끝나면 알림을 받음 - signal 방법 
# 우리가 사용하는 벙법은 비동기방법 (signal)

from django.db.models.signals import post_save

post_save.connect(order_payment_validation, sender=OrderTransaction)

# 만약 OrderTransaction 모델에서 저장 작업이 발생하면 
#   --> order_payment_validation 자동 실행
# 
# views.py의 class OrderImpAjaxView(View)에서 trans.save()가 발생하면
# models.py (본 파일)의 
#   def order_payment_validation(sender, instance, created, *args, **kwargs) 작동
# def order_payment_validation 작동 결과에 따라
#   정상적으로 처리되면 --> views.py의 order.save() 작동
#   비정상적이라면 --> JsonResponse({}, status=401) 리턴
