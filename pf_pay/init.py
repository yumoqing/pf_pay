from ahserver.serverenv import ServerEnv
from pf_pay.ali_pay import Zhifubao_Pay

def load_pf_pay():
	g = ServerEnv()
	zfb = Zhifubao_Pay()
	g.alipay_payment = zfb.alipay_payment
	g.alipay_callback_verify = zfb.alipay_callback_verify

