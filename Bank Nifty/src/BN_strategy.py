# todo - exception handling fr yf api, chk if df.tail() has current day data
# consider 2 sts before exiting

# pip install yfinance
# pip install plyer
# pip install smartapi-python
# pip install websocket-client

import logging
import math
import os
import sys

sys.path.append(r'Bank Nifty\src')  # nopep8
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
from order_placement import buy_order, get_order_status

warnings.filterwarnings("ignore")


time_zone = "Asia/Kolkata"
time_format = "%d-%m-%Y %H:%M"
interval = 5
symbol = "^NSEBANK"
# symbol = "^DJUSBK"

present_day = (dt.now(timezone(time_zone)).today())

shift = timedelta(max(1, (present_day.weekday() + 6) % 7 - 3))
last_business_day = (present_day - shift).strftime("%Y-%m-%d")

weekly_expiry = "BANKNIFTY27JAN22"
instrument_list = None

# last_business_day = "2022-01-24"

call_signal = False
put_signal = False
call_option_price = 0
put_option_price = 0
lot_size = 25
units = 1

title = "ALERT!"
chat_id = "957717113"
token = "5013995887:AAHUu6qsNzw1Bsbq46LThezZBxbGn-E12Tw"
url = f"https://api.telegram.org/bot{token}"


rsi_upper_limit = 95
rsi_lower_limit = 0.5
margin_strike_price_units = 300
rsi_st_index = -1
val_index = -1

st1_length = 7
st1_factor = 1
st2_length = 8
st2_factor = 2
st3_length = 9
st3_factor = 3

logger = None


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


def is_trading_time(timing):
    global call_signal, put_signal

    is_closing_time = dtm(timing.hour, timing.minute) >= dtm(14, 30)

    if timing.hour < 10 or is_closing_time:
        if call_signal:
            call_signal = False
            print(
                f"Warning: Time Out \nCALL Exit: {timing.strftime(time_format)}")
            set_notification(
                f"Warning: Time Out \nCALL Exit: {timing.strftime(time_format)}")

        elif put_signal:
            put_signal = False
            print(
                f"Warning: Time Out \nPUT Exit: {timing.strftime(time_format)}")
            set_notification(
                f"Warning: Time Out \nPUT Exit: {timing.strftime(time_format)}")

        else:
            print("Out of trade timings")
        return False
    return True


def log_signal_msg(super_trend_arr, super_trend_arr_old, close_val, open_val, rsi_val, msg):
    msg = f"Interval : {interval} min \n" + msg
    set_notification(msg)
    print(msg)
    logger.info(
        f"Message : {msg}, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")
    logger.info(
        "---------------------------------------------------------------------------------------------")


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


def signal_alert(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal, put_signal

    print(f"Time: {timing}")
    timing = timing.strftime(time_format)

    logger.info(
        f"Message : 5min Logging, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")
    # print(f"super_trend_arr: {super_trend_arr}")
    # print(f"super_trend_arr_old: {super_trend_arr_old}")
    # print(f"rsi_val: {rsi_val}")
    # print(f"close_val: {close_val}")
    # print(f"open_val: {open_val}")

    if (
        super_trend_arr.all()
        and call_signal is False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
    ):
        set_call_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val)

    if (
        not any(super_trend_arr)
        and put_signal is False
        and close_val < open_val
        and rsi_val > rsi_lower_limit
    ):
        set_put_signal(super_trend_arr, super_trend_arr_old,
                       timing, close_val, open_val, rsi_val)

    if call_signal and not super_trend_arr.all():
        exit_call_signal(super_trend_arr, super_trend_arr_old,
                         timing, close_val, open_val, rsi_val)

    if put_signal and super_trend_arr.any():
        exit_put_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val)


def exit_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global put_signal

    put_signal = False
    msg = f"PUT EXIT !!! {timing}"

    log_signal_msg(super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def exit_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal

    call_signal = False
    msg = f"CALL EXIT !!! {timing}"

    log_signal_msg(super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def set_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global put_signal

    put_signal = True
    msg = None

    price = int(math.floor(close_val / 100.0)) * 100
    price -= margin_strike_price_units

    if not any(super_trend_arr_old):
        msg = f"On going PUT Super Trend !!! {timing}, \nPUT Strike Price: {price} PE"
    else:
        place_order("PE", price)
        msg = f"PUT SIGNAL !!! {timing}, \nPUT Strike Price: {price} PE"

    log_signal_msg(super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def set_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal

    call_signal = True
    msg = None

    price = int(math.ceil(close_val / 100.0)) * 100
    price += margin_strike_price_units

    if super_trend_arr_old.all():
        msg = f"On going Call Super Trend !!! {timing},  \nCALL Strike Price: {price} CE"
    else:
        place_order("CE", price)
        msg = f"CALL SIGNAL !!! {timing},  \nCALL Strike Price: {price} CE"

    log_signal_msg(super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def place_order(signal_type, price):
    global call_option_price, put_option_price
    order_id = None

    if signal_type == "CE":
        call_option_price = price
    else:
        put_option_price = price

    option_tick = str(price) + signal_type
    weekly_option_tick = weekly_expiry + option_tick

    option_price = get_option_price(option_tick)
    token = get_option_token(weekly_option_tick)

    order_id = buy_order(weekly_option_tick, token,
                         option_price, units * lot_size)

    order_status = get_order_status(order_id)
    msg = f"Order Status: {order_status}"
    set_notification(msg)
    print(msg)
    logger.info(msg)


def get_instrument_list():
    global instrument_list

    instrument_list = requests.get(
        r'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json').json()


def get_option_token(trading_symbol):
    token = None
    for tick in instrument_list:
        if tick['symbol'] == trading_symbol:
            token = tick['token']
            break
    return token


def run_code():

    logger.info(
        f"Bank Nifty Strategy Started : {dt.now(timezone(time_zone)).strftime(time_format)}")
    logger.info(
        "---------------------------------------------------------------------------------------------")

    get_instrument_list()

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


logger = get_logger()
run_code()
