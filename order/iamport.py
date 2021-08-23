import requests
from django.conf import settings

# 아임포트와 통신하기 위한 토큰을 받아오는 함수
def get_token():
    access_data = {
        'imp_key': settings.IAMPORT_KEY,
        'imp_secret': settings.IAMPORT_SECRET,
    }

    url = "https://api.iamport.kr/users/getToken"

    req = requests.post(url, data=access_data)
    access_res = req.json() # requests에서 제공하는 json 내장함수

    # 토큰을 정상적으로 받은 경우
    if access_res['code'] is 0:
        return access_res['response']['access_token']
    else: # 토큰 수령 실패
        return None

# 결재 준비: 어떤 주문번호, 얼마 결재할지 아임포트에 미리 정보를 전달
def payment_prepare(order_id, amount, *args, **kwargs):
    
    access_token = get_token() # 위에서 만든 함수 (아이엠포트에서 토큰 받아오기)

    if access_token:
        access_data = {
            'merchant_uid': order_id,
            'amount': amount
        }

        url = 'https://api.iamport.kr/payments/prepare'
        
        headers = {
            'Authorization': access_token,
        }

        req = requests.post(url, data=access_data, headers=headers)
        res = req.json()
        
        if res['code'] != 0:
            raise ValueError('API 통신 오류')
        else:
            pass
    
    else:
        raise ValueError("토큰 오류")

# 결재 완료: 결재 이후 실제 거래와 맞는지를 확인
def find_transaction(order_id, *args, **kwargs):
    access_token = get_token()
    if access_token:
        url = 'https://api.iamport.kr/payments/find/{}'.format(order_id)
        
        headers = {
            'Authorization': access_token,
        }
        
        req = requests.post(url, headers=headers)
        res = req.json()
        
        if res['code'] == 0:
            context = {
                'imp_id': res['response']['imp_uid'],
                'merchant_order_id': res['response']['merchant_uid'],
                'amount': res['response']['amount'],
                'status': res['response']['status'],
                'type': res['response']['pay_method'],
                'receipt_url': res['response']['receipt_url'],
            }
            return context
        else:
            return None
    else:
        return ValueError('토큰 오류')
