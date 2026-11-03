# wechat_h5.py
import time
import json
import secrets
import base64
from urllib.parse import urlparse
from typing import Optional, Dict, Any

import aiohttp
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from appPublic.jsonConfig import getConfig
from .payment_log import new_payment_log


class WechatError(Exception):
    pass


def _now_ts() -> str:
    return str(int(time.time()))


def _nonce_str(n: int = 32) -> str:
    return secrets.token_hex(n // 2)


def _canonical_url_path(url: str) -> str:
    p = urlparse(url)
    path = p.path or "/"
    if p.query:
        return path + "?" + p.query
    return path


def _build_sign_message(method: str, canonical_url: str, timestamp: str, nonce: str, body: str) -> bytes:
    # method \n canonical_url \n timestamp \n nonce \n body \n
    s = "\n".join([method.upper(), canonical_url, timestamp, nonce, body, ""])
    return s.encode("utf-8")

def load_public_key_from_file(fpath, password=None):
    with open(fpath, 'b') as f:
        b = read()
        return serialization.load_pem_public_key(b, password=password)

def load_private_key_from_file(fpath, password=None):
    with open(fpath, 'b') as f:
        b = read()
        return serialization.load_pem_private_key(b, password=password)

def load_private_key(pem_bytes: bytes):
    return serialization.load_pem_private_key(pem_bytes, password=None)


def sign_with_rsa_sha256(private_key, message: bytes) -> str:
    sig = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode()


def verify_rsa_sha256(pubkey, message: bytes, signature_b64: str) -> bool:
    sig = base64.b64decode(signature_b64)
    try:
        pubkey.verify(sig, message, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def aes_gcm_decrypt(api_v3_key: bytes, associated_data: str, nonce: str, ciphertext_b64: str) -> bytes:
    aesgcm = AESGCM(api_v3_key)
    ct = base64.b64decode(ciphertext_b64)
    return aesgcm.decrypt(nonce.encode(), ct, associated_data.encode() if associated_data else None)


class WechatPayClient:
    """
    Async Wechat Pay v3 client for H5 (and basic refund/query).
    - mchid: merchant id
    - serial_no: merchant certificate serial number (string)
    - private_key_pem: merchant private key PEM bytes
    - platform_public_pem: WeChat platform certificate PEM bytes (for notif verify)
    - api_v3_key: 32-byte key (bytes) for AES-GCM decrypt
    config:{
        "pay":{
            "wxpay":{
                "public_key_file":,
                "private_key_file":,
                "mchid":
                "apikey":
                "serial_no":
            }
        }
    }
    """

    BASE = "https://api.mch.weixin.qq.com"

    def __init__(

        self,
        api_v3_key: bytes,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = 15,
    ):
        config = getConfig()
        payinfo = config.pay.wxpay
        self.mchid = payinfo.mchid
        self.serial_no = payinfo.serial_no
        self._private_key = load_private_key_from_file(payinfo.private_key_file)
        self._platform_pub = load_public_key_from_file(payinfo.public_key_file)
        api_v3_key = payinfo.apikey
        if len(api_v3_key) not in (16, 24, 32):
            raise ValueError("api_v3_key must be 16/24/32 bytes (32 recommended)")
        self.api_v3_key = api_v3_key
        self._session = session or aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))

    async def close(self):
        await self._session.close()

    def _build_authorization(self, method: str, path_or_url: str, body: Any):
        if isinstance(body, (dict, list)):
            body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        else:
            body_str = body or ""
        ts = _now_ts()
        nonce = _nonce_str()
        canonical = _canonical_url_path(path_or_url)
        msg = _build_sign_message(method, canonical, ts, nonce, body_str)
        signature = sign_with_rsa_sha256(self._private_key, msg)
        auth = (
            f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mchid}",'
            f'serial_no="{self.serial_no}",nonce_str="{nonce}",timestamp="{ts}",signature="{signature}"'
        )
        return auth, body_str

    async def _request(self, method: str, path: str, json_body: Optional[dict] = None, extra_headers: Optional[dict] = None):
        url = self.BASE + path
        auth_header, body_str = self._build_authorization(method, url, json_body or "")
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        async with self._session.request(method.upper(), url, json=json_body, headers=headers) as resp:
            text = await resp.text()
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = text
            if resp.status >= 400:
                raise WechatError(f"{resp.status} {resp.reason}: {text}")
            return data

    # ----------------- Business APIs -----------------

    async def create_h5_payment(
        self,
        request,
        recharge,
        action) -> str:
        """
        Create H5 payment. Returns the API response which includes 'h5_url'.
        - out_trade_no: merchant order id (unique)
        - description: order title
        - amount_total: total in fen (int)
        - payer_client_ip: user's client IP
        - notify_url: merchant notify URL
        - scene_info: optional dict for H5 info; if None a minimal scene_info will be set
        - attach: optional dict for merchant extra data (will be JSON string)
        """
        path = "/v3/pay/transactions/h5"
        env = request._run_ns
        callback_url= env.entire_url('/pf_pay/wxpay/recharge_callback')
        body = {
            "mchid": self.mchid,
            "out_trade_no": recharge.id,
            "description": "RECHARGE:" + str(recharge.recharge_amt),
            "notify_url": callback_url,
            "amount": {
                "total": recharge.recharge_amt, 
                "currency": recharge.currency or "CNY"
            },
            # attach must be a string per API; we JSON-encode merchant extras
            "attach": json.dumps(attach) if attach else "",
        }
        # scene_info: ensure payer_client_ip included
        if scene_info is None:
            scene_info = {
                "payer_client_ip": request['client_ip'], 
                "h5_info": {"type": "Wap"}
            }
        else:
            scene_info.setdefault("payer_client_ip", request['client_ip'])
        body["scene_info"] = scene_info
        dic = await self._request("POST", path, json_body=body)
        return dic.get('h5_url') or dic.get('mweb_url')

    async def create_native_payment(self, out_trade_no: str, description: str, amount_total: int, notify_url: str, currency: str = "CNY") -> dict:
        """
        Create Native payment (QR code). Returns API response which includes 'code_url'.
        """
        path = "/v3/pay/transactions/native"
        body = {
            "mchid": self.mchid,
            "out_trade_no": out_trade_no,
            "description": description,
            "notify_url": notify_url,
            "amount": {"total": amount_total, "currency": currency},
        }
        return await self._request("POST", path, json_body=body)

    async def refund(self, out_refund_no: str, out_trade_no: str, reason: str, refund_amount: int, total_amount: int) -> dict:
        """
        Refund (domestic). refund_amount & total_amount in fen.
        Path: /v3/refund/domestic/refunds
        """
        path = "/v3/refund/domestic/refunds"
        body = {
            "out_refund_no": out_refund_no,
            "out_trade_no": out_trade_no,
            "reason": reason,
            "amount": {"refund": refund_amount, "total": total_amount, "currency": "CNY"},
        }
        return await self._request("POST", path, json_body=body)

    async def query_order_by_out_trade_no(self, out_trade_no: str, sp_mchid: Optional[str] = None) -> dict:
        p = f"/v3/pay/transactions/out-trade-no/{out_trade_no}"
        if sp_mchid:
            p += f"?sp_mchid={sp_mchid}"
        return await self._request("GET", p)

    async def query_refund(self, out_refund_no: str) -> dict:
        p = f"/v3/refund/domestic/refunds/out-refund-no/{out_refund_no}"
        return await self._request("GET", p)

    # ----------------- Notification utils -----------------

    def verify_notification_signature(self, headers: dict, body: str) -> bool:
        """
        Verify notification signature using platform public key provided at constructor.
        Required headers:
         - Wechatpay-Timestamp
         - Wechatpay-Nonce
         - Wechatpay-Signature
         - Wechatpay-Serial  (optional to check which platform cert used)
        """
        timestamp = headers.get("Wechatpay-Timestamp") or headers.get("wechatpay-timestamp")
        nonce = headers.get("Wechatpay-Nonce") or headers.get("wechatpay-nonce")
        signature = headers.get("Wechatpay-Signature") or headers.get("wechatpay-signature")
        if not (timestamp and nonce and signature):
            return False
        message = "\n".join([timestamp, nonce, body, ""]).encode("utf-8")
        return verify_rsa_sha256(self._platform_pub, message, signature)

    def decrypt_notification_resource(self, resource: dict) -> dict:
        """
        resource example:
        {"algorithm":"AEAD_AES_256_GCM","ciphertext":"...","nonce":"...","associated_data":"..."}
        """
        alg = resource.get("algorithm")
        if alg != "AEAD_AES_256_GCM":
            raise WechatError("Unsupported algorithm: " + str(alg))
        pt = aes_gcm_decrypt(self.api_v3_key, resource.get("associated_data", ""), resource.get("nonce"), resource.get("ciphertext"))
        try:
            return json.loads(pt.decode())
        except Exception:
            return {"raw": pt}


    async def pay_notice_verify(self, request: web.Request):
        body = await request.text()
        headers = dict(request.headers)
        # verify signature
        ok = self.verify_notification_signature(headers, body)
        if not ok:
            return web.Response(status=401, text="invalid signature")
        resource = await request.params_kw.resource
        try:
            dec = self.decrypt_notification_resource(resource)
        except Exception as e:
            return web.Response(status=400, text="decrypt failed")
        return dec
        trade_state = dec.get("trade_state") or dec.get("status")
        rechargeid = dec.get("out_trade_no")
        attach_raw = dec.get("attach")
        merchant_extra = None
        if attach_raw:
            try:
                merchant_extra = json.loads(attach_raw)
            except Exception:
                merchant_extra = attach_raw
        # TODO: implement idempotent order update here, e.g. mark order paid if trade_state == "SUCCESS"

        print("payment notify dec:", dec)
        # respond success
        return web.json_response({"code": "SUCCESS", "message": "OK"})

# 3) refund notify
async def wx_refund_notify(request: web.Request):
    body = await request.text()
    headers = dict(request.headers)
    ok = client.verify_notification_signature(headers, body)
    if not ok:
        return web.Response(status=401, text="invalid signature")
    payload = await request.json()
    resource = payload.get("resource", {})
    try:
        dec = client.decrypt_notification_resource(resource)
    except Exception:
        return web.Response(status=400, text="decrypt failed")
    # dec contains refund info
    print("refund notify dec:", dec)
    # TODO: update refund status idempotently
    return web.json_response({"code": "SUCCESS", "message": "OK"})


# 4) create native (QR) example (returns code_url)
async def create_native(request: web.Request):
    try:
        data = await request.json()
        out_trade_no = data["out_trade_no"]
        description = data["description"]
        amount = int(data["amount"])
        notify_url = data["notify_url"]
        resp = await client.create_native_payment(out_trade_no, description, amount, notify_url)
        return web.json_response(resp)
    except Exception as e:
        return json_error(str(e))


# 5) refund request
async def refund(request: web.Request):
    try:
        data = await request.json()
        out_refund_no = data["out_refund_no"]
        out_trade_no = data["out_trade_no"]
        reason = data.get("reason", "refund")
        refund_amount = int(data["refund_amount"])
        total_amount = int(data["total_amount"])
        resp = await client.refund(out_refund_no, out_trade_no, reason, refund_amount, total_amount)
        return web.json_response(resp)
    except Exception as e:
        return json_error(str(e))


# 6) query order
async def query_order(request: web.Request):
    out_trade_no = request.match_info.get("out_trade_no")
    try:
        resp = await client.query_order_by_out_trade_no(out_trade_no)
        return web.json_response(resp)
    except Exception as e:
        return json_error(str(e))
