# !pip install smartapi-python
# !pip install websocket-client

from smartapi import SmartConnect


def get_account_details():

    obj = SmartConnect(api_key="sKBuEyAI")
    # login api call

    data = obj.generateSession("S1112304", "$upeR123")
    refreshToken = data['data']['refreshToken']

    # fetch the feedtoken
    feedToken = obj.getfeedToken()

    # fetch User Profile
    userProfile = obj.getProfile(refreshToken)

    return obj


def robo_order():
    obj = get_account_details()

    orderparams = {
        "variety": "ROBO",
        "tradingsymbol": "BANKNIFTY27JAN2236400PE",
        "symboltoken": 67868,
        "transactiontype": "BUY",
        "exchange": "NFO",
        "ordertype": "LIMIT",
        "producttype": "BO",
        "duration": "DAY",
        "price": 10.2,
        "squareoff": 10.0,
        "stoploss": 10.0,
        "quantity": 25
    }

    return obj.placeOrder(orderparams)


def buy_order(tradingsymbol, token, price, quantity):
    obj = get_account_details()

    try:
        orderparams = {
            "exchange": "NFO",
            "instrumenttype": "OPTIDX",
            "tradingsymbol": tradingsymbol,  # "BANKNIFTY27JAN2236400PE",
            "quantity": quantity,
            "transactiontype": "BUY",
            "ordertype": "LIMIT",
            "variety": "NORMAL",
            "producttype": "CARRYFORWARD",
            "duration": "DAY",
            "price": price,  # "60",
            "symboltoken": token
        }
        return obj.placeOrder(orderparams)
    except Exception as e:
        print("Order placement failed: {}".format(e))


# not tested

def buy_order_stop_loss():
    obj = get_account_details()

    try:
        orderparams = {
            "exchange": "NFO",
            "instrumenttype": "OPTIDX",
            "tradingsymbol": "BANKNIFTY27JAN2236400PE",
            "quantity": 25,
            "transactiontype": "BUY",
            "ordertype": "STOPLOSS_LIMIT",  # "ordertype": "LIMIT",
            "variety": "STOPLOSS",
            "producttype": "CARRYFORWARD",
            "duration": "DAY",
            "price": "60",
            "triggerprice": "59",
            "stoploss": "20",  # todo - test this param
            "symboltoken": "67868"
        }
        orderId = obj.placeOrder(orderparams)
        print("The order id is: {}".format(orderId))
    except Exception as e:
        print("Order placement failed: {}".format(e))


def get_order_status(order_id):
    obj = get_account_details()

    orders = obj.orderBook()['data']
    for ord in orders:
        if ord['orderid'] == order_id:
            return f"Order Status: {ord['status']}" + f"Order Text: {ord['text']}"
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


# not tested


def modify_order(order_id, current_price):
    obj = get_account_details()

    orderparams = {
        "variety": "NORMAL",
        "orderid": order_id,
        "ordertype": "LIMIT",
        "producttype": "CARRYFORWARD",
        "transactiontype": "SELL",
        "duration": "DAY",
        "price": current_price,
        "quantity": 25,
        "tradingsymbol": "BANKNIFTY27JAN2236400PE",
        "symboltoken": "67868",
        "exchange": "NFO"
    }

    return obj.modifyOrder(orderparams)

# not tested


def sell_order(order_id, exit_price):
    obj = get_account_details()

    try:
        orderparams = {
            "variety": "NORMAL",
            "orderid": order_id,
            "ordertype": "LIMIT",
            "producttype": "CARRYFORWARD",
            "transactiontype": "SELL",
            "duration": "DAY",
            "miit PRICE": exit_price,  # todo - check
            "quantity": 25,
            "tradingsymbol": "BANKNIFTY27JAN2236400PE",
            "symboltoken": "67868",
            "exchange": "NFO"
        }
        orderId = obj.placeOrder(orderparams)
        print("The order id is: {}".format(orderId))
    except Exception as e:
        print("Order placement failed: {}".format(e))


if __name__ == "__main__":
    # buy_order("BANKNIFTY27JAN2236400PE", 67868, 21, 25)
    # buy_order_stop_loss()
    oid = robo_order()
    get_order_details(oid)
    get_order_details_full(oid)
    # get_order_status("220124000688087")
    # sell_order("220124000653844", 80)
    # modify_order("220124000688087", 80)
