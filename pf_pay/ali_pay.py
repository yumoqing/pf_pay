from appPublic.jsonConfig import getConfig
from appPublic.worker import awaitify
from appPublic.log import debug, info, exception, error
from alipay import AliPay

class Zhifubao_Pay:
	"""
	config:{
		"pay":{
			"alipay":{
				"public_key_file":,
				"private_key_file":,
				"appid":
				"callback":
			}
		}
	}
	"""
	def __init__(self):
		config = getConfig()
		pubfile = config.pay.alipay.public_key_file
		prifile = config.pay.alipay.private_key_file
		appid = config.pay.alipay.appid
		self.callback = config.pay.alipay.callback
		"""
			支付宝支付
			传递参数:
			out_trade_no : 订单
			total_amount : 金额
			subject : 产品
		"""
		with open(pubfile, 'r') as f:
			alipay_public_key_string = f.read()
		with open(prifile, 'r') as f:
			app_private_key_string = f.read()
		#alipay_appid = '2021005111636494'
		self.alipay = AliPay(
			appid=appid,
			app_notify_url=self.callback,  # 默认回调url
			app_private_key_string=app_private_key_string,
			# 支付宝的公钥，验证支付宝回传消息使用，不是自己的公钥,
			alipay_public_key_string=alipay_public_key_string,
			sign_type="RSA2",  # RSA 或者 RSA2
			debug=False,  # 默认False
		)

		
	async def alipay_payment(self, out_trade_no, total_amount, subject):
		order_string = self.alipay.api_alipay_trade_page_pay(
			# 订单号
			out_trade_no=out_trade_no,
			# 金额
			total_amount=total_amount,
			# 产品
			subject=subject,
			# 回调地址和默认配置一样即可
			return_url=self.callback,
			notify_url=self.callback  # 可选, 不填则使用默认notify url
		)
		url = f"https://openapi.alipay.com/gateway.do?{order_string}"
		return url
	
	async def alipay_callback_verify(self, data, sign):
		f = awaitify(self.alipay.verify)
		r = await f(data, sign)
		return r
