# todo - exception handling fr yf api, add a chk to determine if df.tail() has current day data
# chk order status(open/completed/closed) before selling on exit. got msg as selling order placed but order was complete. but logic working fine
# stoploss implementation

# pip install yfinance
# pip install plyer
# pip install smartapi-python
# pip install websocket-client
# pip install pandas_ta

# region imports

import os
import sys

sys.path.append(os.getcwd() + r'\src\modules')  # nopep8

import logging
import math
import os
import time
import warnings
from datetime import datetime as dt
from datetime import time as dtm
from datetime import timedelta

import pandas_ta as ta
import pandas as pd

import requests
import yfinance as yf
from get_option_data import get_option_price
from indicators import rsi, supertrend
from order_placement import (cancel_order, get_instrument_list,
                             get_order_status, robo_order,
                             sell_order_market)
from plyer import notification
from pytz import timezone

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
# last_business_day = "2022-02-03"

# endregion

# region order placement vars

weekly_expiry = "BANKNIFTY17FEB22"
instrument_list = None
call_signal = False
put_signal = False
call_option_price = 0
put_option_price = 0
trading_symbol = None
option_token = None
quantity = 25
buy_order_id = None
target_sell_order_id = None
stop_loss_sell_order_id = None
margin = 10

# endregion

# region notification and log vars

title = "ALERT!"
chat_id = "957717113"
chatbot_token = "5013995887:AAHUu6qsNzw1Bsbq46LThezZBxbGn-E12Tw"
url = f"https://api.telegram.org/bot{chatbot_token}"
logger = None

# endregion

# region strategy vars

symbol = "^NSEBANK"
# symbol = "^DJUSBK"

# (10, 1.2, 7, 2.4, 9, 3.6, 5, 95, 0.05, 14, 275) - 90.77% - 64

#     st1_length = params[0]
#     st1_factor = params[1]
#     st2_length = params[2]
#     st2_factor = params[3]
#     st3_length = params[4]
#     st3_factor = params[5]
#     rsi_period = params[6]
#     rsi_upper_limit = params[7]
#     rsi_lower_limit = params[8]
#     ema_length = params[9]
#     bb_width_min = params[10]

bb_width_min = 275
ema_length = 14
rsi_period = 5
rsi_upper_limit = 95
rsi_lower_limit = 0.05
margin_strike_price_units = 500
val_index = -1
st1_length = 10
st1_factor = 1.2
st2_length = 7
st2_factor = 2.4
st3_length = 9
st3_factor = 3.6

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
    requests.get(f"{url}/sendMessage", params=params, verify=False)


def log_notification(logging_required, super_trend_arr=None, super_trend_arr_old=None, close_val=None, open_val=None, rsi_val=None, msg=None, ema_val=None):
    msg = f"Interval : {interval} min \n {msg}"
    set_notification(msg)
    print(msg)
    if logging_required:
        logger.info(
            f"Message : {msg}, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, EMA:{ema_val}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")
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

    is_closing_time = dtm(timing.hour, timing.minute) >= dtm(14, 30)

    if timing.hour < 10 or is_closing_time:
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


def signal_alert(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width):
    print(f"Time: {timing}")
    timing = timing.strftime(time_format)

    logger.info(
        f"Message : Interval {interval} min, Close: {close_val}, Open: {open_val}, RSI: {rsi_val}, EMA: {ema_val}, super_trend_arr: {super_trend_arr}, super_trend_arr_old: {super_trend_arr_old}")

    call_strategy(super_trend_arr, super_trend_arr_old,
                  timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width)

    put_strategy(super_trend_arr, super_trend_arr_old,
                 timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width)


def put_strategy(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width):
    global put_signal

    if (
        bb_width > bb_width_min
        and not any(super_trend_arr)
        and put_signal is False
        and close_val < open_val
        and rsi_val > rsi_lower_limit
        and high_val < ema_val
    ):
        set_put_signal(super_trend_arr, super_trend_arr_old,
                       timing, close_val, open_val, rsi_val, ema_val)

    if put_signal and super_trend_arr.any():
        exit_put_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val)


def call_strategy(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width):
    global call_signal

    if (
        bb_width > bb_width_min
        and super_trend_arr.all()
        and call_signal is False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
        and low_val > ema_val
    ):
        set_call_signal(super_trend_arr, super_trend_arr_old,
                        timing, close_val, open_val, rsi_val, ema_val)

    if call_signal and not super_trend_arr.all():
        exit_call_signal(super_trend_arr, super_trend_arr_old,
                         timing, close_val, open_val, rsi_val)


def exit_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global put_signal

    put_signal = False

    msg = f"PUT EXIT !!! {timing}"

    log_notification(True, super_trend_arr, super_trend_arr_old,
                     close_val, open_val, rsi_val, msg)

    if buy_order_id:
        exit_order()


def exit_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal

    call_signal = False

    msg = f"CALL EXIT !!! {timing}"

    log_notification(True, super_trend_arr, super_trend_arr_old,
                     close_val, open_val, rsi_val, msg)

    if buy_order_id:
        exit_order()


def set_put_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, ema_val):
    global put_signal

    put_signal = True
    msg = None

    strike_price = int(math.floor(close_val / 100.0)) * 100
    strike_price -= margin_strike_price_units

    # purchasing at market price
    # option_price = get_option_price(str(strike_price) + "PE")
    option_price = 0

    if not any(super_trend_arr_old):
        msg = f"On going PUT Super Trend !!! {timing}, \nPUT Strike Price: {strike_price} PE, \nOption Price:  {option_price}"
    else:
        msg = f"PUT SIGNAL !!! {timing}, \nPUT Strike Price: {strike_price} PE, \nOption Price:  {option_price}"

    log_notification(True, super_trend_arr, super_trend_arr_old,
                     close_val, open_val, rsi_val, msg, ema_val)

    place_order("PE", strike_price, option_price)


def set_call_signal(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val, ema_val):
    global call_signal

    call_signal = True
    msg = None

    strike_price = int(math.ceil(close_val / 100.0)) * 100
    strike_price += margin_strike_price_units

    # purchasing at market price
    # option_price = get_option_price(str(strike_price) + "PE")
    option_price = 0

    if super_trend_arr_old.all():
        msg = f"On going Call Super Trend !!! {timing},  \nCALL Strike Price: {strike_price} CE, \nOption Price:  {option_price}"
    else:
        msg = f"CALL SIGNAL !!! {timing},  \nCALL Strike Price: {strike_price} CE, \nOption Price:  {option_price}"

    log_notification(True, super_trend_arr, super_trend_arr_old,
                     close_val, open_val, rsi_val, msg, ema_val)

    place_order("CE", strike_price, option_price)

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
    global call_option_price, put_option_price, buy_order_id, stop_loss_sell_order_id, trading_symbol, option_token

    if signal_type == "CE":
        call_option_price = strike_price
    else:
        put_option_price = strike_price

    option_tick = str(strike_price) + signal_type
    trading_symbol = weekly_expiry + option_tick

    option_token = get_option_token(trading_symbol)

    # call robo order here. rest of the lines not required
    buy_result = robo_order(trading_symbol, option_token,
                            option_price, quantity)
    if buy_result['status'] == 201:
        buy_order_id = buy_result['order_id']
        buy_order_status = get_order_status(buy_order_id)
        log_notification(
            True, msg=f"Buy Order Status: {buy_order_status}")
    else:
        log_notification(True, msg=buy_result['msg'])


def exit_order():
    global buy_order_id

    # sell robo order
    # check order status before selling
    log_notification(
        True, msg="Exiting orders. Please check the orders manually")

    # if order not yet executed. todo check order status before calling
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
    df["RSI"] = rsi(df, periods=rsi_period)
    df["EMA"] = ta.ema(df["Close"], length=ema_length)

    bollinger_band = ta.bbands(df["Close"], length=20, std=2)[
        ["BBL_20_2.0", "BBU_20_2.0"]]
    df["Bollinger_Width"] = bollinger_band["BBU_20_2.0"] - \
        bollinger_band["BBL_20_2.0"]

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
        df['Bollinger_Width'][val_index]
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

    log_notification(
        True, msg=f"Bank Nifty Strategy Started(dd-mm-yyyy) : {dt.now(timezone(time_zone)).strftime(time_format)} \nLast business day(dd-mm-yyyy): {(present_day - shift).strftime('%d-%m-%Y')}")

    if instrument_list:
        logger.info("Instrument list downloaded")

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

        if res == 0:
            indicator_calc_signal_generation()
            sleep_time_in_secs = (60 - timing.second) + (interval - 1) * 60
            print(
                f"Sleep Time: {(interval - 1)} min {(60 - timing.second)} sec")

            time.sleep(sleep_time_in_secs)
        else:
            sleep_time = interval - res
            print(f"Sleep Time: {sleep_time} min")
            time.sleep(sleep_time * 60)

# endregion

# region Method call


if __name__ == "__main__":
    logger = get_logger()
    run_code()

# endregion

# endregion
