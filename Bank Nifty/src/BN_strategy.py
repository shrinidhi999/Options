# todo - exception handling fr yf api, add a chk to determine if df.tail() has current day data


# pip install yfinance
# pip install plyer
# pip install smartapi-python
# pip install websocket-client

# region imports

import sys

sys.path.append(r'Bank Nifty\src')  # nopep8

import logging
import math
import os
import time
import warnings
from datetime import datetime as dt
from datetime import time as dtm
from datetime import timedelta

import requests
import yfinance as yf
from plyer import notification
from pytz import timezone

from get_option_data import get_option_price
from indicators import rsi, supertrend
from order_placement import buy_order, get_instrument_list, get_order_status, sell_order_limit, sell_order_market, cancel_order

warnings.filterwarnings("ignore")

# endregion

# region vars

# region time vars

time_zone = "Asia/Kolkata"
time_format = "%d-%m-%Y %H:%M"
interval = 5
present_day = (dt.now(timezone(time_zone)).today())

shift = timedelta(max(1, (present_day.weekday() + 6) % 7 - 3))
last_business_day = (present_day - shift).strftime("%Y-%m-%d")
# last_business_day = "2022-01-25"

# endregion

# region order placement vars

weekly_expiry = "BANKNIFTY03FEB22"
instrument_list = None
call_signal = False
put_signal = False
call_option_price = 0
put_option_price = 0
trading_symbol = None
quantity = 25
buy_order_id = None
sell_order_id = None
margin = 20

# endregion

# region notification and log vars

title = "ALERT!"
chat_id = "957717113"
token = "5013995887:AAHUu6qsNzw1Bsbq46LThezZBxbGn-E12Tw"
url = f"https://api.telegram.org/bot{token}"
logger = None

# endregion

# region strategy vars

symbol = "^NSEBANK"
# symbol = "^DJUSBK"

rsi_upper_limit = 95
rsi_lower_limit = 0.5
margin_strike_price_units = 400
rsi_st_index = -1
val_index = -1

st1_length = 7
st1_factor = 1
st2_length = 8
st2_factor = 2
st3_length = 9
st3_factor = 3

# endregion

# endregion

# region methods

# region Notification and Logging


def get_logger():

    if not os.path.exists('logs'):
        os.makedirs('logs')

    logging.basicConfig(filename=os.getcwd() + f"\\Logs\\BN_Logs_{present_day.strftime('%d-%m-%Y')}.log",
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
    requests.get(url + "/sendMessage", params=params, verify=False)


def log_signal_msg(logging_required, super_trend_arr=None, super_trend_arr_old=None, close_val=None, open_val=None, rsi_val=None, msg=None):
    msg = f"Interval : {interval} min \n" + msg
    set_notification(msg)
    print(msg)
    if logging_required:
        logger.info(
            f"Message : {msg}, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")
        logger.info(
            "---------------------------------------------------------------------------------------------")
# endregion

# region Data download


def download_data():
    df = None
    try:
        df = yf.download(symbol, start=last_business_day,
                         period="1d", interval=str(interval) + "m")

        logger.info(
            "---------------------------------------------------------------------------------------------")
        logger.info(
            f"DF downloaded : {df.head(3)}")
        # Suppose the API called at 10.11am. The API returns 5m data till 10.10am and 1m data related to 10.11am.
        # since our logic is for 5min data, we need to drop the 1m data.
        if df.index[-1].minute % interval != 0:
            df.drop(df.index[-1], inplace=True)
        logger.info(
            f"DF updated : {df.tail(3)}")

    except Exception as e:
        print(e.message)
        set_notification(f"Error: {e.message}")
        logger.error(f"Error: {e.message}")

    return df
# endregion

# region Strategy


def is_trading_time(timing):
    global call_signal, put_signal

    is_closing_time = dtm(timing.hour, timing.minute) >= dtm(14, 30)

    if timing.hour < 10 or is_closing_time:
        if call_signal:
            call_signal = False
            log_signal_msg(
                True, msg=f"Warning: Time Out \nCALL Exit: {timing.strftime(time_format)}")

        elif put_signal:
            put_signal = False
            log_signal_msg(
                True, msg=f"Warning: Time Out \nPUT Exit: {timing.strftime(time_format)}")
        else:
            print("Out of trade timings")
        return False
    return True


def signal_alert(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    print(f"Time: {timing}")
    timing = timing.strftime(time_format)

    logger.info(
        f"Message : 5min Logging, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")

    call_strategy(super_trend_arr, super_trend_arr_old,
                  timing, close_val, open_val, rsi_val)

    put_strategy(super_trend_arr, super_trend_arr_old,
                 timing, close_val, open_val, rsi_val)


def put_strategy(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global put_signal

    if (
        not any(super_trend_arr)
        and put_signal is False
        and close_val < open_val
        and rsi_val > rsi_lower_limit
    ):
        set_put_signal(super_trend_arr, super_trend_arr_old,
                       timing, close_val, open_val, rsi_val)

    if put_signal and super_trend_arr.any():
        exit_put_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val)


def call_strategy(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal

    if (
        super_trend_arr.all()
        and call_signal is False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
    ):
        set_call_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val)

    if call_signal and not super_trend_arr.all():
        exit_call_signal(super_trend_arr, super_trend_arr_old,
                         timing, close_val, open_val, rsi_val)


def exit_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global put_signal

    put_signal = False
    exit_order()

    msg = f"PUT EXIT !!! {timing}"

    log_signal_msg(True, super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def exit_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal

    call_signal = False
    exit_order()

    msg = f"CALL EXIT !!! {timing}"

    log_signal_msg(True, super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def set_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global put_signal

    put_signal = True
    msg = None

    strike_price = int(math.floor(close_val / 100.0)) * 100
    strike_price -= margin_strike_price_units
    option_price = get_option_price(str(strike_price) + "PE")

    if not any(super_trend_arr_old):
        msg = f"On going PUT Super Trend !!! {timing}, \nPUT Strike Price: {strike_price} PE, \nOption Price:  {option_price}"
    else:
        place_order("PE", strike_price, option_price)
        msg = f"PUT SIGNAL !!! {timing}, \nPUT Strike Price: {strike_price} PE"

    log_signal_msg(True, super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def set_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal

    call_signal = True
    msg = None

    strike_price = int(math.ceil(close_val / 100.0)) * 100
    strike_price += margin_strike_price_units
    option_price = get_option_price(str(strike_price) + "CE")

    if super_trend_arr_old.all():
        msg = f"On going Call Super Trend !!! {timing},  \nCALL Strike Price: {strike_price} CE, \nOption Price:  {option_price}"
    else:
        place_order("CE", strike_price, option_price)
        msg = f"CALL SIGNAL !!! {timing},  \nCALL Strike Price: {strike_price} CE"

    log_signal_msg(True, super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)

# endregion

# region Order placement


def get_option_token(trading_symbol):
    token = None
    for tick in instrument_list:
        if tick['symbol'] == trading_symbol:
            token = tick['token']
            break
    return token


def place_order(signal_type, strike_price, option_price):
    global call_option_price, put_option_price, buy_order_id, sell_order_id, trading_symbol

    if signal_type == "CE":
        call_option_price = strike_price
    else:
        put_option_price = strike_price

    option_tick = str(strike_price) + signal_type
    trading_symbol = weekly_expiry + option_tick

    token = get_option_token(trading_symbol)

    buy_result = buy_order(trading_symbol, token,
                           option_price, quantity)

    if buy_result['status'] == 201:

        buy_order_id = buy_result['order_id']
        buy_order_status = get_order_status(buy_order_id)

        if 'complete' in buy_order_status:
            sell_result = sell_order_limit(
                buy_order_id, trading_symbol, token, quantity, option_price + margin)

            if sell_result['status'] == 201:
                sell_order_id = sell_result['order_id']
                sell_order_status = get_order_status(sell_order_id)
                log_signal_msg(
                    True, msg=f"Buy Order Status: {buy_order_status}  \nSell Order Status: {sell_order_status}")
            else:
                log_signal_msg(
                    True, msg=f"Buy Order Status: {buy_order_status}  \nSell Order Status: {sell_result['msg']}")
        else:
            log_signal_msg(
                True, msg=f"Buy Order Status: {buy_order_status}")

    else:
        log_signal_msg(True, msg=buy_result['msg'])


def exit_order():
    cancel_order(sell_order_id, "NORMAL")
    sell_result = sell_order_market(
        buy_order_id, trading_symbol, token, quantity)
    log_signal_msg(
        True, msg=f"Sell Order Status: {sell_result['msg']}")

# endregion


# region run method


def run_code():
    global last_business_day, instrument_list

    print(f"Last Business Day : {last_business_day}")
    inp = input("Please confirm : Yes(Y) or No(N) : ")

    if inp.lower() in ["y", "yes"]:
        print("Thanks for the confirmation")
    else:
        last_business_day = input(
            "Please enter the last business day(yyyy-mm-dd) : ")

    print("Last business day : ", last_business_day)

    instrument_list = get_instrument_list()

    logger.info(
        f"Bank Nifty Strategy Started : {dt.now(timezone(time_zone)).strftime(time_format)}")

    logger.info(f"Last business day: {last_business_day}")

    if len(instrument_list) > 0:
        logger.info("Instrument list downloaded")

    logger.info(
        "---------------------------------------------------------------------------------------------")

    while True:
        timing = dt.now(timezone(time_zone))
        print("-----------------------------------------")
        print(f'Time: {timing.strftime(time_format)}')

        res = timing.minute % interval

        if is_trading_time(timing) and res == 1:
            sleep_time_in_secs = (60 - timing.second) + (interval - 1) * 60
            print(
                f"Sleep Time: {(interval - 1)} min {(60 - timing.second)} sec")

            df = download_data()
            df["ST_7"] = supertrend(df, st1_length, st1_factor)["in_uptrend"]
            df["ST_8"] = supertrend(df, st2_length, st2_factor)["in_uptrend"]
            df["ST_9"] = supertrend(df, st3_length, st3_factor)["in_uptrend"]
            df["RSI"] = rsi(df)

            super_trend_arr = df.iloc[rsi_st_index][[
                "ST_7", "ST_8", "ST_9"]].values
            super_trend_arr_old = df.iloc[rsi_st_index -
                                          1][["ST_7", "ST_8", "ST_9"]].values

            signal_alert(
                super_trend_arr,
                super_trend_arr_old,
                df.index[val_index],
                df["Close"][val_index],
                df["Open"][val_index],
                df["RSI"][rsi_st_index],
            )
            time.sleep(sleep_time_in_secs)
        else:
            res = 5 if res == 0 else res
            sleep_time = interval - res + 1
            print(f"Sleep Time: {sleep_time} min")
            time.sleep(sleep_time * 60)

# endregion

# region Method call


logger = get_logger()
run_code()

# endregion

# endregion
