# !pip install smartapi-python
# !pip install websocket-client
import os

import requests
from joblib import Memory
from smartapi import SmartConnect

cache_dir = os.getcwd()
mem = Memory(cache_dir)
trailing_stop_loss = 5

user_name = None
pwd = None
api_key = None
file_path = f'{os.getcwd()}\\src\\credentials.txt'

if os.path.exists(file_path):
    with open(file_path, "r") as file:
        creds = file.read().split('\n')
        user_name = creds[0].split(' = ')[1]
        pwd = creds[1].split(' = ')[1]
        api_key = creds[2].split(' = ')[1]


@mem.cache(verbose=0)
def get_instrument_list():
    try:
        return requests.get(
            r'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json').json()
    except:
        return None


def clear_cache():
    get_instrument_list.clear()


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


def get_order_status(order_id):
    try:
        obj = get_account_details()

        orders = obj.orderBook()['data']
        for ord in orders:
            if ord['orderid'] == order_id:
                return f" {ord['status']}, Text:  {ord['text']}"
        return 'Not Found'
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


def robo_order(trading_symbol, token, price, quantity, square_off=20, stoploss=40):
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
            "squareoff": square_off,
            "stoploss": stoploss,
            "trailingStopLoss": trailing_stop_loss,
            "quantity": quantity,
            "disclosedquantity": quantity
        }
        order_id = obj.placeOrder(orderparams)
        return {"status": 201, "order_id": order_id, "msg": "Robo Order Placed"}

    except Exception as e:
        return {"status": 501, "msg": f"Robo order failed. Exception : {e}"}


def sell_order_market(order_id, trading_symbol, token, quantity, variety):
    try:
        obj = get_account_details()
        orderparams = {
            "variety": variety,
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
        order_id = obj.placeOrder(orderparams)
        return {"status": 201, "order_id": order_id, "msg": "Sell Order Placed"}

    except Exception as e:
        return {"status": 501, "msg": f"Sell order failed. Exception : {e}"}


def cancel_order(order_id, variety):
    try:
        obj = get_account_details()
        return obj.cancelOrder(order_id, variety)
    except Exception as e:
        return {"status": 501, "msg": f"Cancel order failed. Exception : {e}"}


if __name__ == "__main__":
    # pass
    # buy robo order
    # res = robo_order("BANKNIFTY03FEB2238200PE", 45276, 50, 25)['order_id']
    # get_order_status(res)
    # sell robo order
    # res_sel = sell_order_market(res, "BANKNIFTY03FEB2238200PE", 45276, 25)
    clear_cache()
