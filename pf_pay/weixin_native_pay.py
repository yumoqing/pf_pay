import time
import json
import random
import string
import io

import requests

from base64 import b64encode
from urllib.parse import urlparse
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import pkcs1_15
from Cryptodome.Hash import SHA256
import qrcode
from appPublic.jsonConfig import getConfig
from ahserver.globalEnv import save_file
from appPublic.uniqueID import getID

class WXPay:
    """ 微信 Native支付
    """

    def __init__(self):
        self.appid = "wx892972c8fb1005b4"  # APPID
        self.mchid = "1682646155"  # 商户号
        self.payment_url = 'https://api.mch.weixin.qq.com/v3/pay/transactions/native'  # Native支付下单接口
        self.refund_url = 'https://api.mch.weixin.qq.com/v3/refund/domestic/refunds'  # 退款接口
        self.notify_url = "https://www.kaiyuancloud.cn/dev/customer/get_weixpay.dspy"  # 通知url
        self.serial_no = '7B8C3F6F573F249EDD3ED6AA95EC632691BCB503'  # 商户证书序列号

    # 生成签名
    def get_sign(self, sign_str):
        config = getConfig()
        # 线上证书路径
        apiclient_key = config.weixinpay.private
        rsa_key = RSA.importKey(open(apiclient_key).read())
        signer = pkcs1_15.new(rsa_key)
        digest = SHA256.new(sign_str.encode('utf8'))
        sign = b64encode(signer.sign(digest)).decode('utf-8')
        return sign

    def request(self, url: str, method: str, data: dict = None):
        data = json.dumps(data) if data else ''
        random_str = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
        timestamp = str(int(time.time()))
        sign_str = '\n'.join([
            method.upper(),  # HTTP请求方法
            url.split(urlparse(url).netloc)[-1],  # path+args
            timestamp,  # 时间戳
            random_str,  # 请求随机串
            data, ''  # 请求报文主体
        ])  # 结尾空窜仅用于让后面多一个\n
        sign = self.get_sign(sign_str)

        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Authorization': f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mchid}",nonce_str="{random_str}",signature="{sign}",timestamp="{timestamp}",serial_no="{self.serial_no}"'
        }
        response = requests.request(url=url, method=method, data=data, headers=headers)
        return response

    # # 支付
    async def payment(self, order_no, total, description):
        data = {
            "mchid": self.mchid,
            "out_trade_no": order_no,  # 订单号
            "appid": self.appid,
            "description": description,  # 商品描述
            "notify_url": self.notify_url,
            "amount": {
                "total": total,  # 总金额(分)
                "currency": "CNY"
            }
        }
        num = self.request(self.payment_url, 'POST', data)
        # 生成二维码
        img = qrcode.make(num.json()['code_url'])
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0, 0)
        byt = buf.read()
        imgurl = await save_file(byt, getID()+'.png')
        return imgurl

    # 退款
    def refund(self, transaction_id, out_refund_no, refund, reason):
        data = {
            "transaction_id": transaction_id,  # 微信支付订单号(交易单号)
            "out_refund_no": out_refund_no,  # 商户退款单号(商户单号)
            "reason": reason,  # 退款原因
            "notify_url": self.notify_url,  # 通知Url
            "amount": {
                "total": refund,  # 订单金额
                "refund": refund,  # 退款金额(分)
                "currency": "CNY"
            }
        }
        return self.request(self.refund_url, 'POST', data)

    def application_bill(self):
        url = 'https://api.mch.weixin.qq.com/v3/bill/tradebill?bill_date=2022-02-28&bill_type=ALL'
        return self.request(url, 'GET')



async def pay_wx(order_no, total, description):
    result = await WXPay().payment(order_no, total, description)
    return result
