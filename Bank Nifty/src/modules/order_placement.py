# !pip install smartapi-python
# !pip install websocket-client
import os
import requests
from smartapi import SmartConnect

user_name = None
pwd = None
api_key = None

with open(os.getcwd() + "\src\credentials.txt", "r") as file:
    creds = file.read().split('\n')
    user_name = creds[0].split(' = ')[1]
    pwd = creds[1].split(' = ')[1]
    api_key = creds[2].split(' = ')[1]


def get_instrument_list():
    try:
        return requests.get(
            r'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json').json()
    except:
        return None


def get_account_details():
    try:
        obj = SmartConnect(api_key=api_key)
        # login api call

        data = obj.generateSession(user_name, pwd)
        refreshToken = data['data']['refreshToken']

        # fetch the feedtoken
        feedToken = obj.getfeedToken()

        # fetch User Profile
        userProfile = obj.getProfile(refreshToken)

        return obj

    except Exception as e:
        print(f"Exception : {e}")
        return None


def buy_order(trading_symbol, token, price, quantity):
    try:
        obj = get_account_details()
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
    try:
        obj = get_account_details()

        orders = obj.orderBook()['data']
        for ord in orders:
            if ord['orderid'] == order_id:
                return f"Order Status: {ord['status']}, Text:  {ord['text']}"
        return 'Not Found'
    except Exception as e:
        print(f"Exception : {e}")


def get_order_details():
    try:
        obj = get_account_details()

        orders = obj.orderBook()['data']
        for ord in orders:
            print(f"Order Id: {ord['orderid']}")
            print(f"Symbol: {ord['tradingsymbol']}")
            print(f"Price: {ord['price']}")
            print(f"Order Status: {ord['status']}")
            print(f"Order Text: {ord['text']}")
            print("-------------")
    except Exception as e:
        print(f"Exception : {e}")


def get_order_details_full(order_id):
    try:
        obj = get_account_details()

        orders = obj.orderBook()['data']
        for ord in orders:
            if ord['orderid'] == order_id:
                print(ord)
    except Exception as e:
        print(f"Exception : {e}")


def robo_order(trading_symbol, token, price, quantity):
    try:
        obj = get_account_details()
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
            "squareoff": 20,
            "stoploss": 40,
            "trailingStopLoss": 5,
            "quantity": quantity,
            "disclosedquantity": quantity
        }
        return {"status": 201, "order_id": obj.placeOrder(orderparams), "msg": "Sell Order Placed"}
    except Exception as e:
        print('catch blk')
        return {"status": 501, "msg": f"Sell order failed. Exception : {e}"}


def sell_order_limit(order_id, trading_symbol, token, quantity, price):
    try:
        obj = get_account_details()
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
    try:
        obj = get_account_details()
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
    try:
        obj = get_account_details()
        return obj.cancelOrder(order_id, variety)
    except Exception as e:
        return {"status": 501, "msg": f"Cancel order failed. Exception : {e}"}


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

    # res = robo_order("BANKNIFTY03FEB2238200PE", 45276, 50, 25)['order_id']
    # get_order_status(res)
    # res_sel = sell_order_market(res, "BANKNIFTY03FEB2238200PE", 45276, 25)
    # sell robo order
    # sell_result = sell_order_market(
    #     buy_oid, "BANKNIFTY03FEB2238200PE", 45276, 25)
    get_order_details()
    # get_order_details_full(res_sel)
    # get_order_status(220124000688087)
