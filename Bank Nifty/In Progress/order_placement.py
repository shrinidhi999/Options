# !pip install smartapi-python
# !pip install websocket-client

# or from smartapi.smartConnect import SmartConnect
from smartapi import SmartConnect
# import smartapi.smartExceptions(for smartExceptions)

# create object of call
obj = None


def get_account_details():
    global obj

    obj = SmartConnect(api_key="sKBuEyAI")
    # login api call

    data = obj.generateSession("S1112304", "$upeR123")
    refreshToken = data['data']['refreshToken']

    # fetch the feedtoken
    feedToken = obj.getfeedToken()

    # fetch User Profile
    userProfile = obj.getProfile(refreshToken)


def buy_order():
    try:
        orderparams = {
            "exchange": "NFO",
            "instrumenttype": "OPTIDX",
            "tradingsymbol": "BANKNIFTY27JAN2237900CE",
            "quantity": 25,
            "transactiontype": "BUY",
            "ordertype": "LIMIT",
            "variety": "NORMAL",
            "producttype": "CARRYFORWARD",
            "duration": "DAY",
            "price": "60",
            # "stoploss":"20", todo - test this param
            "symboltoken": "67912"
        }
        orderId = obj.placeOrder(orderparams)
        print("The order id is: {}".format(orderId))
    except Exception as e:
        print("Order placement failed: {}".format(e))


# not tested
def buy_order_stop_loss():
    try:
        orderparams = {
            "exchange": "NFO",
            "instrumenttype": "OPTIDX",
            "tradingsymbol": "BANKNIFTY27JAN2237900CE",
            "quantity": 25,
            "transactiontype": "BUY",
            "ordertype": "STOPLOSS_LIMIT",  # "ordertype": "LIMIT",
            "variety": "STOPLOSS",
            "producttype": "CARRYFORWARD",
            "duration": "DAY",
            "price": "60",
            "triggerprice": "59",
            # "stoploss":"20", todo - test this param
            "symboltoken": "67912"
        }
        orderId = obj.placeOrder(orderparams)
        print("The order id is: {}".format(orderId))
    except Exception as e:
        print("Order placement failed: {}".format(e))


def get_order_details():
    orders = obj.orderBook()['data']
    sample = None
    for ord in orders:
        print(f"Order Id: {ord['orderid']}")
        print(f"Symbol: {ord['tradingsymbol']}")
        print(f"Price: {ord['price']}")
        print(f"Order Status: {ord['status']}")
        print("-------------")


def sell_order(exit_price):
    try:
        orderparams = {
            "variety": "NORMAL",
            "orderid": "210823000463560",
            "ordertype": "LIMIT",
            "producttype": "CARRYFORWARD",
            "transactiontype": "SELL",
            "duration": "DAY",
            "price": exit_price,  # todo - check
            "quantity": "1",
            "tradingsymbol": "BANKNIFTY27JAN2237900CE",
            "symboltoken": "67912",
            "exchange": "NFO"
        }
        orderId = obj.placeOrder(orderparams)
        print("The order id is: {}".format(orderId))
    except Exception as e:
        print("Order placement failed: {}".format(e))


get_account_details()
buy_order()
buy_order_stop_loss()
get_order_details()
sell_order(exit_price)
