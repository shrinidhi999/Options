# !pip install smartapi-python
# !pip install websocket-client
import requests
from smartapi import SmartConnect

user_name = "S1112304"
pwd = "$upeR123"
api_key = "cLgcIydO"


def get_instrument_list():

    return requests.get(
        r'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json').json()


def get_account_details():

    obj = SmartConnect(api_key=api_key)
    # login api call

    data = obj.generateSession(user_name, pwd)
    refreshToken = data['data']['refreshToken']

    # fetch the feedtoken
    feedToken = obj.getfeedToken()

    # fetch User Profile
    userProfile = obj.getProfile(refreshToken)

    return obj


def buy_order(trading_symbol, token, price, quantity):
    obj = get_account_details()

    try:
        orderparams = {
            "exchange": "NFO",
            "instrumenttype": "OPTIDX",
            "tradingsymbol": trading_symbol,  # "BANKNIFTY27JAN2236400PE",
            "quantity": quantity,
            "transactiontype": "BUY",
            "ordertype": "LIMIT",
            "variety": "NORMAL",
            "producttype": "CARRYFORWARD",
            "duration": "DAY",
            "price": price,  # "60",
            "symboltoken": token
        }
        return {"status": 201, "order_id": obj.placeOrder(orderparams), "msg": "Buy Order Placed"}
    except Exception as e:
        return {"status": 501, "msg": f"Buy order failed. Exception : {e}"}


def get_order_status(order_id):
    obj = get_account_details()

    orders = obj.orderBook()['data']
    for ord in orders:
        if ord['orderid'] == order_id:
            return f"Order Status: {ord['status']}, Text:  {ord['text']}"
    return 'Not Found'


def get_order_details(order_id):
    obj = get_account_details()

    orders = obj.orderBook()['data']
    for ord in orders:
        if ord['orderid'] == order_id:
            print(f"Order Id: {ord['orderid']}")
            print(f"Symbol: {ord['tradingsymbol']}")
            print(f"Price: {ord['price']}")
            print(f"Order Status: {ord['status']}")
            print(f"Order Text: {ord['text']}")
            print("-------------")


def get_order_details_full(order_id):
    obj = get_account_details()

    orders = obj.orderBook()['data']
    for ord in orders:
        if ord['orderid'] == order_id:
            print(ord)


def robo_order(trading_symbol, token, price, quantity):
    obj = get_account_details()
    try:
        orderparams = {
            "variety": "ROBO",
            "tradingsymbol": trading_symbol,
            "symboltoken": token,
            "transactiontype": "BUY",
            "exchange": "NFO",
            "ordertype": "LIMIT",
            "producttype": "BO",
            "duration": "DAY",
            "price": price,
            "squareoff": price+20,
            "stoploss": price-30,
            "trailingStopLoss": 5,
            "quantity": quantity,
            "disclosedquantity": quantity
        }
        print('try blk')
        return {"status": 201, "order_id": obj.placeOrder(orderparams), "msg": "Sell Order Placed"}
    except Exception as e:
        print('catch blk')
        return {"status": 501, "msg": f"Sell order failed. Exception : {e}"}


def sell_order_limit(order_id, trading_symbol, token, quantity, price):
    obj = get_account_details()

    try:
        orderparams = {
            "variety": "NORMAL",
            "orderid": order_id,
            "ordertype": "LIMIT",
            "producttype": "CARRYFORWARD",
            "transactiontype": "SELL",
            "duration": "DAY",
            "price": price,
            "quantity": quantity,
            "tradingsymbol": trading_symbol,
            "symboltoken": token,
            "exchange": "NFO"
        }
        return {"status": 201, "order_id": obj.placeOrder(orderparams), "msg": "Sell Order Placed"}
    except Exception as e:
        return {"status": 501, "msg": f"Sell order failed. Exception : {e}"}


def sell_order_market(order_id, trading_symbol, token, quantity):
    obj = get_account_details()

    try:
        orderparams = {
            "variety": "NORMAL",
            "orderid": order_id,
            "ordertype": "MARKET",
            "producttype": "CARRYFORWARD",
            "transactiontype": "SELL",
            "duration": "DAY",
            "quantity": quantity,
            "tradingsymbol": trading_symbol,
            "symboltoken": token,
            "exchange": "NFO"
        }
        return {"status": 201, "order_id": obj.placeOrder(orderparams), "msg": "Sell Order Placed"}
    except Exception as e:
        return {"status": 501, "msg": f"Sell order failed. Exception : {e}"}


def cancel_order(order_id, variety):
    obj = get_account_details()
    return obj.cancelOrder(order_id, variety)


if __name__ == "__main__":
    # # Place buy order when signal comes
    # buy_oid = buy_order("BANKNIFTY27JAN2238200CE", 67918, 0.40, 25)
    # sell_oid = None

    # # place sell order with margin 20 pts(last param)
    # if 'complete' in get_order_status(buy_oid):
    #     sell_oid = sell_order_limit(
    #         buy_oid, "BANKNIFTY27JAN2238200PE", 67918, 25, 15)

    # # if exit signal comes, cancel the order
    # cancel_order(sell_oid, "NORMAL")

    # # sell the order at market price
    # sell_order_market(buy_oid, "BANKNIFTY27JAN2238200PE", 67918, 25)

    res = robo_order("BANKNIFTY03FEB2238200PE", 45276, 50, 25)['order_id']
    get_order_status(res)
    res_sel = sell_order_market(res, "BANKNIFTY03FEB2238200PE", 45276, 25)
    # sell robo order
    # sell_result = sell_order_market(
    #     buy_oid, "BANKNIFTY03FEB2238200PE", 45276, 25)
    # get_order_details(sell_id)
    # get_order_details_full(res_sel)
    # get_order_status("220124000688087")
