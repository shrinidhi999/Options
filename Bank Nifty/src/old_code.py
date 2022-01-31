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
