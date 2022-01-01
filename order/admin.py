import csv
import datetime #파이썬 내장모듈
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe


# 추가로 필요한 모델 등록
from .models import Order, OrderItem
from django.http import HttpResponse


def order_detail(obj):
    url = reverse('orders:admin_order_detail', args=[obj.id])
    html = mark_safe("<a href='{}'>Detail</a>".format(url))
    return html
order_detail.short_description = 'Detail'

def order_pdf (obj):
    url = reverse('orders:admin_order_pdf', args=[obj.id])
    html = mark_safe("<a href='{}'>PDF</a>".format(url))
    return html
order_pdf.short_description = 'PDF'

def export_to_csv(modeladmin, request, queryset):
# 모델에 등록된 fields를 가져올 수 있음
    opts = modeladmin.model._meta
    
    # 요청이 왔을 경우, 답변(response) 형태를 정의
    # HttpResponse 임포트 해주어야 함
    response = HttpResponse(content_type='text/csv')

    # HttpResponse 다운로드 형태(다운로드 파일 이름) 지정 
    # (오타에 민감 -> 스펠링 주의할 것)
    response['Content-Disposition'] = 'attachment;filename={}.csv'.format(opts.verbose_name)

    # 다운로드 파일에 포함될 내용을 기록
    # 파이썬 내장 모듈 csv를 임포트 해주어야 함
    # csv.writer(매개변수) -> 매개변수는 파일이어야 함
    # HTTP Response 결국 파일 형태로 보내는 것이므로 문제 없음
    writer = csv.writer(response)

    # csv에 필요한 fields를 설정
    # 기본적으로 장고 모델의 각 아이템에는 
    # field.many_to_many 및 field.one_to_many에 대하여
    # True/False가 지정되어 있음
    # 우리는 하나의 필드에 하나의 값이 있는 것만 선택함
    fields = [
        field for field in opts.get_fields() if not field.many_to_many and not field.one_to_many
    ]

    # csv 파일의 필드를 기록 
    # (엑셀의 맨 첫번째 제목 줄 -> Title Row)
    # 주문id, 이름, 성, 이메일, ...
    #  2       길동, 홍, ㅇㅇ@ㅇㅇ.ㅇㅇㅇ
    writer.writerow(
        [field.verbose_name for field in fields]
    )

    # csv 파일의 실제 정보를 기록
    # 실제 데이터가 들어있는 queryset은 함수의 
    # 매개변수로 정보를 받음
    for obj in queryset:
        data_row = []
        for field in fields:
            value = getattr(obj, field.name) # 쿼리셋 객체의 이름(실제로는 데이터 값)을 뽑아옴
            # 날짜/시간 정보인 경우 csv에 맞게 변형
            # strftime 참고 블로그: https://bit.ly/3vAoO5t
            # 파이썬 내장 모듈인 datetime을 임포트 해야 함
            if isinstance(value, datetime.datetime):
                value = value.strftime('%Y-%m-%d') 
            data_row.append(value)
        writer.writerow(data_row)
    
    # 위에서 처리한 내용이 담겨진 response를 리턴함
    return response

# 관라자 페이지의 action에 표시할 이름
# 'export_to_csv'를 호출하는 이름을 설정
export_to_csv.short_description = 'Export to CSV'

class OrderItemInline(admin.TabularInline):
    
    # Order와 연결하여 보여줄 모델을 설정
    # 우리는 주문에 대한 주문 아이템을 연결함
    model = OrderItem
    
    # product가 ForeignKey로 묶여 있으면 
    # 모든 Product가 표시되고 선택박스(select box)로 선택
    # 내용이 많으면 디스플레이가 많고 스크롤을 많이 해야되고 번잡함
    # raw_id_fields를 설정하면 값을 Text로 입력하고 
    # 검색버튼을 활용하여 보다 편리하게 검색 가능
    raw_id_fields = ['product']

# 관리자 페이지에 보여주기 위한 정보 등록을 위한 클래스 코딩
class OrderAdmin(admin.ModelAdmin):
    
    # 관리자 페이지에 Display 해줄 목록을 등록
    list_display = [
        'id', 
        'first_name', 
        'last_name', 
        'email',
        'address',
        'postal_code',
        'city',
        'paid',
        'created',
        'updated',

        # Custom Display 함수 추가
        order_detail,
        order_pdf,
    ]
    
    # 필터링 걸어줄 목록을 등록
    list_filter = [
        'paid',
        'created',
        'updated',
    ]

    # Order 모델과 ForeignKey로 연결된 모델들을 같이 표시
    # 유사한 내용을 하나의 페이지에서 확인
    # 별도로 클래스를 만들어서 구현 -> 우리는 OrderItemInline 생성
    inlines = [OrderItemInline]
    
    # 관리자 페이지의 Action에 추가 기능을 부여
    # 우리는 엑셀로 관리할 수 있도록 csv 파일을 출력하는 기능 추가
    actions = [export_to_csv]

# 관리자 페이지에 Order를 Display 하는데
# OrderAdmin 옵션들을 적용하여 보여줄것이다.
admin.site.register(Order, OrderAdmin)