# todo - exception handling fr yf api, add a chk to determine if df.tail() has current day data
# chk order status(open/completed/closed) before selling on exit. got msg as selling order placed but order was complete. but logic working fine
# call/put signal is given but order placement fails, then set signal = false. so that it checks the params in the next 5min and tries to place the order
# if the stoploss/target hits, then set signal to false. To accomplish this we need to check the status of order regularly

# pip install yfinance
# pip install plyer
# pip install smartapi-python
# pip install websocket-client
# pip install pandas_ta

# region imports

import os
import sys

sys.path.append(f"{os.getcwd()}\src\modules")  # nopep8

import logging
import math
import os
import time
import warnings
from datetime import datetime as dt
from datetime import time as dtm
from datetime import timedelta

import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf
from indicators import atr, rsi, supertrend
from oi_scraper import get_web_driver, get_oi_data, close_driver
from order_placement import (cancel_order, clear_cache, get_instrument_list,
                             get_order_status, robo_order, sell_order_market)
from pandas.tseries.offsets import BDay
from plyer import notification
from pytz import timezone

warnings.filterwarnings("ignore")

# endregion

# region vars

# region time vars

time_zone = "Asia/Kolkata"
time_format = "%d-%m-%Y %H:%M"

present_day = (dt.now(timezone(time_zone)).today())

# endregion

# region order placement vars

instrument_list = None
call_signal = False
put_signal = False
trading_symbol = None
option_token = None
quantity = 50
buy_order_id = None

call_strike_price = 0
put_strike_price = 0
stoploss = 0
# endregion

# region notification and log vars

title = "ALERT!"
chat_id = "957717113"
chatbot_token = "5013995887:AAHUu6qsNzw1Bsbq46LThezZBxbGn-E12Tw"
url = f"https://api.telegram.org/bot{chatbot_token}"
logger = None

# endregion

# region strategy vars

symbol = "^NSEI"
# symbol = "^DJUSBK"

weekly_expiry = "NIFTY24MAR22"
margin_strike_price_units = 0

params = (10, 1, 10, 2.4, 10, 3, 5, 95, 0.05, 55, 75, 10,
          1.5, 2, 2, '2022-03-15', 0.7, 12, 750000, 35)


st1_length = params[0]
st1_factor = params[1]
st2_length = params[2]
st2_factor = params[3]
st3_length = params[4]
st3_factor = params[5]
rsi_period = params[6]
rsi_upper_limit = params[7]
rsi_lower_limit = params[8]
ema_length = params[9]
bb_width_min = params[10]
margin = params[11]
stoploss_factor = params[12]
atr_period = params[13]
interval = params[14]
last_business_day = params[15]  # "2022-02-15"
margin_factor = params[16]
bb_length = params[17]
min_oi_diff = params[18]
max_loss_units = params[19]

val_index = -1
min_target_units = 5

# endregion

# endregion

# region methods

# region Notification and Logging


def get_logger():

    if not os.path.exists('logs'):
        os.makedirs('logs')

    logging.basicConfig(filename=os.getcwd() + f"\\Logs\\Nifty_Logs_{present_day.strftime('%d-%m-%Y')}.log",
                        format='%(message)s',
                        filemode='w')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger


def set_notification(msg):
    notification.notify(title=title, message=msg, timeout=25)
    send_mobile_notification(msg)


def send_mobile_notification(msg):
    params = {"chat_id": chat_id, "text": msg}
    requests.get(f"{url}/sendMessage", params=params, verify=False)


def log_notification(logging_required, super_trend_arr=None, super_trend_arr_old=None, close_val=None, open_val=None, rsi_val=None, msg=None, ema_val=None, bb_width=None):
    msg = f"Interval : {interval} min \n {msg}"
    set_notification(msg)
    print(msg)
    if logging_required:
        logger.info(
            f"Message : {msg}, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, EMA:{ema_val}, BB Width: {bb_width}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")
        logger.info(
            "---------------------------------------------------------------------------------------------")

# endregion

# region Data download


def download_data():
    df = None
    try:
        df = yf.download(symbol, start=last_business_day,
                         period="1d", interval=f"{str(interval)}m")

        # df = df[df.index.minute % interval == 0]

        logger.info(
            "---------------------------------------------------------------------------------------------")
        logger.info(
            f"DF downloaded : {df.tail(5)}")
        # In all the sites for 5min chart there is a delay. Ex. if we check for 10am candle, it gets completed at 10.04am
        # since our logic is for 5min data, we need to drop the last candle data.
        # if df.index[-1].minute % interval != 0:
        #     df.drop(df.index[-1], inplace=True)

        df.drop(df.index[-1], inplace=True)
        logger.info(
            f"DF updated : {df.tail(5)}")

    except (UnboundLocalError, Exception) as e:
        print('Download failed')
        set_notification(f'Error: {e.message}')
        logger.error(f'Error: {e.message}')
    return df
# endregion

# region Strategy


def is_trading_time(timing):
    global call_signal, put_signal

    is_closing_time = dtm(timing.hour, timing.minute) > dtm(14, 30)
    is_opening_time = dtm(timing.hour, timing.minute) < dtm(9, 30)

    if is_opening_time or is_closing_time:
        clear_cache()
        # close_driver()

        if call_signal:
            call_signal = False
            log_notification(
                True, msg=f"Warning: Time Out \nCALL Exit: {timing.strftime(time_format)}")

        elif put_signal:
            put_signal = False
            log_notification(
                True, msg=f"Warning: Time Out \nPUT Exit: {timing.strftime(time_format)}")
        else:
            print("Out of trade timings")
        return False
    return True


def verify_oi_diff(order_type):
    diff_dict = get_oi_data()

    call_oi, put_oi = diff_dict['call_oi'], diff_dict['put_oi']
    oi_diff = abs(call_oi - put_oi)

    logger.info(
        f"OI Change: Order Type : {order_type},  OI diff: {oi_diff}, Call OI: {call_oi}, Put OI: {put_oi}")

    if call_signal or put_signal:
        if 0 in (oi_diff, call_oi, put_oi):
            return True

    elif oi_diff >= min_oi_diff:
        if ((order_type == 'CE') and (call_oi < put_oi)) or ((order_type == 'PE') and (call_oi > put_oi)):
            return True

    return False


def signal_alert(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width, atr_val, prev_close_val, prev_open_val):
    global call_signal, put_signal, call_strike_price, put_strike_price

    print(f"Time: {timing}")
    timing = timing.strftime(time_format)

    logger.info(
        f"Message : Interval {interval} min, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, EMA: {ema_val}, BB width: {bb_width}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")

    # Keeping this code commented as sometimes option price may not move as quickly as market price.
    # if call_signal:
    #     if (low_val <= (call_strike_price - stoploss)) or (high_val >= (call_strike_price + margin)):
    #         call_signal = put_signal = False
    #         call_strike_price = put_strike_price = 0

    # elif put_signal:
    #     if (high_val >= (put_strike_price + stoploss)) or (low_val <= (put_strike_price - margin)):
    #         call_signal = put_signal = False
    #         call_strike_price = put_strike_price = 0

    call_strategy(super_trend_arr, super_trend_arr_old,
                  timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width, atr_val, prev_close_val, prev_open_val)

    put_strategy(super_trend_arr, super_trend_arr_old,
                 timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width, atr_val, prev_close_val, prev_open_val)


def put_strategy(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width, atr_val, prev_close_val, prev_open_val):
    global put_signal

    if (
        call_signal == False
        and put_signal == False
        and bb_width >= bb_width_min
        and not any(super_trend_arr)
        and close_val < open_val
        and rsi_val > rsi_lower_limit
        and open_val < ema_val
        and verify_oi_diff('PE')
        # and open_val < prev_close_val
        # and open_val < prev_open_val
    ):

        set_put_signal(super_trend_arr, super_trend_arr_old,
                       timing, close_val, open_val, rsi_val, ema_val, atr_val, bb_width)

    if put_signal and ((super_trend_arr[0] == True) and (verify_oi_diff('PE') == False)):
        exit_put_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val)


def call_strategy(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width, atr_val, prev_close_val, prev_open_val):
    global call_signal
    if (
        call_signal == False
        and put_signal == False
        and bb_width >= bb_width_min
        and super_trend_arr.all()
        and close_val > open_val
        and rsi_val < rsi_upper_limit
        and open_val > ema_val
        and verify_oi_diff('CE')
        # and open_val > prev_close_val
        # and open_val > prev_open_val
    ):
        set_call_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val, ema_val, atr_val, bb_width)

    if call_signal and ((super_trend_arr[0] == False) and (verify_oi_diff('CE') == False)):
        exit_call_signal(super_trend_arr, super_trend_arr_old,
                         timing, close_val, open_val, rsi_val)


def exit_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global put_signal

    put_signal = False

    msg = f"PUT EXIT !!! {timing}"

    log_notification(True, super_trend_arr=super_trend_arr, super_trend_arr_old=super_trend_arr_old,
                     close_val=close_val, open_val=open_val, rsi_val=rsi_val, msg=msg)

    if buy_order_id:
        exit_order()


def exit_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal

    call_signal = False

    msg = f"CALL EXIT !!! {timing}"

    log_notification(True, super_trend_arr=super_trend_arr, super_trend_arr_old=super_trend_arr_old,
                     close_val=close_val, open_val=open_val, rsi_val=rsi_val, msg=msg)

    if buy_order_id:
        exit_order()


def set_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, ema_val, atr_val, bb_width):
    global put_signal

    put_signal = True
    msg = None

    strike_price = int(math.floor(close_val / 50.0)) * 50
    strike_price -= margin_strike_price_units

    # purchasing at market price
    # option_price = get_option_price(str(strike_price) + "PE")
    option_price = 0

    stoploss = atr_val * stoploss_factor
    margin_val = atr_val * margin_factor
    # stoploss = stoploss_factor

    if not any(super_trend_arr_old):
        msg = f"On going PUT Super Trend !!! {timing}, \nPUT Strike Price: {strike_price} PE, \nStop Loss:  {stoploss}, \nMargin: {margin_val}"
    else:
        msg = f"PUT SIGNAL !!! {timing}, \nPUT Strike Price: {strike_price} PE, \nStop Loss:  {stoploss}, \nMargin: {margin_val}"

    log_notification(True, super_trend_arr=super_trend_arr, super_trend_arr_old=super_trend_arr_old,
                     close_val=close_val, open_val=open_val, rsi_val=rsi_val, msg=msg, ema_val=ema_val, bb_width=bb_width)

    place_order("PE", strike_price, option_price, margin_val, stoploss)


def set_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, ema_val, atr_val, bb_width):
    global call_signal

    call_signal = True
    msg = None

    strike_price = int(math.ceil(close_val / 50.0)) * 50
    strike_price += margin_strike_price_units

    # purchasing at market price
    # option_price = get_option_price(str(strike_price) + "PE")
    option_price = 0

    stoploss = atr_val * stoploss_factor
    margin_val = atr_val * margin_factor
    # stoploss = stoploss_factor

    if super_trend_arr_old.all():
        msg = f"On going Call Super Trend !!! {timing},  \nCALL Strike Price: {strike_price} CE, \nStop Loss:  {stoploss}, \nMargin: {margin_val}"
    else:
        msg = f"CALL SIGNAL !!! {timing},  \nCALL Strike Price: {strike_price} CE, \nStop Loss:  {stoploss}, \nMargin: {margin_val}"

    log_notification(True, super_trend_arr=super_trend_arr, super_trend_arr_old=super_trend_arr_old,
                     close_val=close_val, open_val=open_val, rsi_val=rsi_val, msg=msg, ema_val=ema_val, bb_width=bb_width)

    place_order("CE", strike_price, option_price, margin_val, stoploss)

# endregion

# region Order placement


def get_option_token(trading_symbol):
    return next(
        (
            tick['token']
            for tick in instrument_list
            if tick['symbol'] == trading_symbol
        ),
        None,
    )


def place_order(signal_type, strike_price, option_price, margin_val, stoploss_val):
    global buy_order_id, trading_symbol, option_token, margin, stoploss, call_strike_price, put_strike_price

    if signal_type == "CE":
        call_strike_price = strike_price
    else:
        put_strike_price = strike_price

    stoploss_val = min(stoploss_val, max_loss_units)
    stoploss_val = max_loss_units if math.isnan(stoploss_val) else stoploss_val

    margin_val = min_target_units if math.isnan(margin_val) else margin_val

    margin = margin_val
    stoploss = stoploss_val

    option_tick = str(strike_price) + signal_type
    trading_symbol = weekly_expiry + option_tick

    option_token = get_option_token(trading_symbol)

    buy_result = robo_order(trading_symbol, option_token,
                            option_price, quantity, margin_val, stoploss_val)
    if buy_result['status'] == 201:
        buy_order_id = buy_result['order_id']
        buy_order_status = get_order_status(buy_order_id)
        log_notification(
            True, msg=f"Buy Order Status: {buy_order_status}")
    else:
        log_notification(True, msg=buy_result['msg'])


def exit_order():
    global buy_order_id

    # check order status before selling
    log_notification(
        True, msg="Exiting orders. Please check the orders manually")

    # if order not yet executed. todo check order status before cancelling
    cancel_result = cancel_order(buy_order_id, "ROBO")

    # if order is executed. todo check order status before calling
    sell_result = sell_order_market(
        buy_order_id, trading_symbol, option_token, quantity, "ROBO")
    log_notification(
        True, msg=f"Cancel Order result: {cancel_result} \nSell Order Status: {sell_result['msg']}")

    buy_order_id = None


# endregion


# region run method


def indicator_calc_signal_generation():
    df = download_data()
    df["ST_7"] = supertrend(df, st1_length, st1_factor)["in_uptrend"]
    df["ST_8"] = supertrend(df, st2_length, st2_factor)["in_uptrend"]
    df["ST_9"] = supertrend(df, st3_length, st3_factor)["in_uptrend"]
    df["ATR"] = atr(df, atr_period)
    df["RSI"] = rsi(df, periods=rsi_period)
    df["EMA"] = ta.ema(df["Close"], length=ema_length)

    bollinger_band = ta.bbands(df["Close"], length=bb_length, std=2)[
        [f"BBL_{bb_length}_2.0", f"BBU_{bb_length}_2.0"]]
    df["Bollinger_Width"] = bollinger_band[f"BBU_{bb_length}_2.0"] - \
        bollinger_band[f"BBL_{bb_length}_2.0"]

    super_trend_arr = df.iloc[val_index][[
        "ST_7", "ST_8", "ST_9"]].values
    super_trend_arr_old = df.iloc[val_index -
                                  1][["ST_7", "ST_8", "ST_9"]].values

    signal_alert(
        super_trend_arr,
        super_trend_arr_old,
        df.index[val_index],
        df["Close"][val_index],
        df["Open"][val_index],
        df["RSI"][val_index],
        df["High"][val_index],
        df["Low"][val_index],
        df["EMA"][val_index],
        df["Bollinger_Width"][val_index],
        df["ATR"][val_index],
        df["Close"][val_index - 1],
        df["Open"][val_index - 1]
    )


def initial_set_up():
    global last_business_day, instrument_list

    print(f"Last Business Day(yyyy-mm-dd) : {last_business_day}")
    inp = input("Please confirm : Yes(Y) or No(N) : ")

    if inp.lower() in ["y", "yes"]:
        print("Thanks for the confirmation")
    else:
        last_business_day = input(
            "Please enter the last business day(yyyy-mm-dd) : ")

    print("Last business day(yyyy-mm-dd) : ", last_business_day)
    print("Weekly Expiry: ", weekly_expiry)

    instrument_list = get_instrument_list()
    get_web_driver()

    log_notification(
        True, msg=f"Nifty Strategy Started(dd-mm-yyyy) : {dt.now(timezone(time_zone)).strftime(time_format)} \nLast business day(yyyy-mm-dd): {last_business_day}")

    if instrument_list:
        log_notification(
            True, msg=f"Instrument list downloaded and OI data check:{get_oi_data()}")

    else:
        log_notification(True, msg="Instrument list download failed")

    logger.info(
        "---------------------------------------------------------------------------------------------")


def run_code():

    initial_set_up()

    while True:
        timing = dt.now(timezone(time_zone))
        print("-----------------------------------------")
        print(f'Time: {timing.strftime(time_format)}')

        res = timing.minute % interval

        if is_trading_time(timing) and res == 1:
            indicator_calc_signal_generation()
            sleep_time_in_secs = (60 - timing.second) + (interval - 1) * 60
            print(
                f"Sleep Time: {(interval - 1)} min {(60 - timing.second)} sec")

            time.sleep(sleep_time_in_secs)
        else:
            # sleep_time = interval - res
            sleep_time = 1
            print(f"Sleep Time: {sleep_time} min")
            time.sleep(sleep_time * 60)

# endregion

# region Method call


if __name__ == "__main__":
    logger = get_logger()
    run_code()

# endregion

# endregion
