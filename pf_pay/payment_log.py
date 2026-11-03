from sqlor.dbpools import DBPools
from appPublic.timeUtils import timestampstr

async def new_payment_log(request, params_kw=None):
    db = DBPools()
    env = request._run_ns
    if not params_kw:
        params_kw = env.params_kw
    dbname = env.get_module_dbname('pf_pay')
    userid = await env.get_user()
    userorgid = await env.get_userorgid()
    async with db.sqlorContext(dbname) as sor:
        ts = timestampstr()
        ns = {
            "id": ts + getID(),
            "notify_url": env.entire_url(f'/pf_pay/{params_kw.payment_channel}/callback.dspy'),
            "customerid": userorgid,
            "userid": userid,
            "payment_channel": params_kw.payment_channel,
            "payment_name": params_kw.payment_name,
            "amount_total": params_kw.amount_total,
            "payer_client_ip": request['client_ip'],
            "currency": params_kw.currency,
            "payment_status": "0",
            "init_timestamp": ts
        }
        await sor.C('payment_log', ns.copy())
        return ns
    return None


