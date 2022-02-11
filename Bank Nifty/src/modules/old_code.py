# code to place normal buy order
def place_order(signal_type, strike_price, option_price):
    global call_option_price, put_option_price, buy_order_id, target_sell_order_id, stop_loss_sell_order_id, trading_symbol, option_token

    if signal_type == "CE":
        call_option_price = strike_price
    else:
        put_option_price = strike_price

    option_tick = str(strike_price) + signal_type
    trading_symbol = weekly_expiry + option_tick

    option_token = get_option_token(trading_symbol)

    buy_result = buy_order(trading_symbol, option_token,
                           option_price, quantity)

    if buy_result['status'] == 201:

        buy_order_id = buy_result['order_id']
        buy_order_status = get_order_status(buy_order_id)

        if 'complete' in buy_order_status:
            target_sell_result = sell_order_limit(
                buy_order_id, trading_symbol, option_token, quantity, option_price + margin)

            if target_sell_result['status'] == 201:
                target_sell_order_id = target_sell_result['order_id']
                sell_order_status = get_order_status(target_sell_order_id)
                log_notification(
                    True, msg=f"Buy Order Status: {buy_order_status}  \nSell Order Status: {sell_order_status}")
            else:
                log_notification(
                    True, msg=f"Buy Order Status: {buy_order_status}  \nSell Order Status: {target_sell_result['msg']}")
        else:
            log_notification(
                True, msg=f"Buy Order Status: {buy_order_status}")

    else:
        log_notification(True, msg=buy_result['msg'])


# code to exit order when normal orders are placed
def exit_order():
    global buy_order_id, target_sell_order_id

    log_notification(
        True, msg="Exiting orders. Please check the orders manually")

    cancel_order(target_sell_order_id, "NORMAL")
    sell_result = sell_order_market(
        buy_order_id, trading_symbol, option_token, quantity)
    log_notification(
        True, msg=f"Sell Order Status: {sell_result['msg']}")

    buy_order_id = None
    target_sell_order_id = None


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
