import os
import paypalrestsdk
from paypalrestsdk import Payment

paypalrestsdk.config({
	"mode":"sandbox",
	"client_id":"your id",
	"client_secret":"your secret"
})

class TransItem:
	class __init__(self, itemid, name, price, currency, quantity):
		self.id = itemid
		self.name = name
		self.price = price
		self.currency = currency
		self.quantity = quantity
	
	def dic(self):
		return {
			"name":self.name,
			"sku":self.id,
			"price":self.price,
			"currency":self.currency,
			"quantity":self.quantity
		}

class OrderGoods:
	
class Paypal_Pay:
	def __init__(self):
		config = getConfig()
		self.client_id = config.paypal.client_id
		self.client_secret = config.paypal.client_secret
		self.client_mode = "SANDBOX"
	
	def get_products(self):
		credentials = {
			'client_id' : self.client_id,
			'client_secret':self.client_secret,
			'client_mode':self.client_mode
		}
		result = Products(credentials=credentials).list_product()
		payload = result.payload()
		return payload
	

