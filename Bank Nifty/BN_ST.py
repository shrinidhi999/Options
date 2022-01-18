# pip install yfinance
# pip install plyer

# todo getting dates correctly - mon to fri
# todo sleep times need to calculate at sec level: add loggers
# check super_trend_arr: super_trend_arr_old: super_trend_arr_old should be same as prev super_trend_arr

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

warnings.filterwarnings("ignore")

time_zone = "Asia/Kolkata"
time_format = "%d-%m-%Y %H:%M"
interval = 5
symbol = "^NSEBANK"
# symbol = "^DJUSBK"

present_today = (dt.now(timezone(time_zone)).today() -
                 timedelta(days=1)).strftime("%Y-%m-%d")
present_today = "2022-01-17"

call_signal = False
put_signal = False

title = "ALERT!"
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
    logging.basicConfig(filename=os.getcwd() + "\\BN_Logs.log",
                        format='%(message)s',
                        filemode='w')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger


def tr(data):
    data["previous_close"] = data["Close"].shift(1)
    data["high-low"] = abs(data["High"] - data["Low"])
    data["high-pc"] = abs(data["High"] - data["previous_close"])
    data["low-pc"] = abs(data["Low"] - data["previous_close"])
    return data[["high-low", "high-pc", "low-pc"]].max(axis=1)


def atr(data, period):
    data["tr"] = tr(data)
    return data["tr"].rolling(period).mean()


def supertrend(df, period, atr_multiplier):
    hl2 = (df["High"] + df["Low"]) / 2
    df["atr"] = atr(df, period)
    df["upperband"] = hl2 + (atr_multiplier * df["atr"])
    df["lowerband"] = hl2 - (atr_multiplier * df["atr"])
    df["in_uptrend"] = True

    for current in range(1, len(df.index)):

        previous = current - 1

        if df["Close"][current] > df["upperband"][previous]:
            df["in_uptrend"][current] = True

        elif df["Close"][current] < df["lowerband"][previous]:
            df["in_uptrend"][current] = False

        else:
            df["in_uptrend"][current] = df["in_uptrend"][previous]

            if (
                df["in_uptrend"][current]
                and df["lowerband"][current] < df["lowerband"][previous]
            ):
                df["lowerband"][current] = df["lowerband"][previous]

            if (
                not df["in_uptrend"][current]
                and df["upperband"][current] > df["upperband"][previous]
            ):
                df["upperband"][current] = df["upperband"][previous]
    return df


def rsi(df, periods=2, ema=True):
    """
    Returns a pd.Series with the relative strength index.
    """

    close_delta = df["Close"].diff()

    # Make two series: one for lower closes and one for higher closes

    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)

    if ema is True:
        # Use exponential moving average
        ma_up = up.ewm(com=periods - 1, adjust=True,
                       min_periods=periods).mean()
        ma_down = down.ewm(com=periods - 1, adjust=True,
                           min_periods=periods).mean()

    else:
        # Use simple moving average
        ma_up = up.rolling(window=periods, adjust=False).mean()
        ma_down = down.rolling(window=periods, adjust=False).mean()

    rsi = ma_up / ma_down
    rsi = 100 - (100 / (1 + rsi))
    return rsi


def set_notification(msg):
    # pass
    notification.notify(title=title, message=msg, timeout=25)
    send_mobile_notification(msg)


def send_mobile_notification(msg):
    params = {"chat_id": "957717113", "text": msg}
    requests.get(url + "/sendMessage", params=params, verify=False)


def is_trading_time(timing):
    global call_signal, put_signal

    is_closing_time = dtm(timing.hour, timing.minute) >= dtm(14, 30)

    if timing.hour < 10 or is_closing_time:
        if call_signal:
            call_signal = False
            print(
                f"Warning: Time Out \nCALL Exit: {timing.strftime(time_format)}")

        elif put_signal:
            put_signal = False
            print(
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
    df = yf.download(symbol, start=present_today,
                     period="1d", interval=str(interval) + "m")
    logger.info(
        f"DF downloaded : {df.tail(3)}")
    # Suppose the API called at 10.11am. The API returns 5m data till 10.10am and 1m data related to 10.11am.
    # since our logic is for 5min data, we need to drop the 1m data.
    if df.index[-1].minute % interval != 0:
        df.drop(df.tail(1).index, inplace=True)
    logger.info(
        f"DF updated : {df.tail(3)}")
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
        msg = f"On going PUT SIGNAL !!! {timing}, \nPUT Strike Price: {price} PE"
    else:
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
        msg = f"On going CALL SIGNAL !!! {timing},  \nCALL Strike Price: {price} CE"
    else:
        msg = f"CALL SIGNAL !!! {timing},  \nCALL Strike Price: {price} CE"

    log_signal_msg(super_trend_arr, super_trend_arr_old,
                   close_val, open_val, rsi_val, msg)


def run_code():
    logger.info(
        f"Bank Nifty Strategy Started : {dt.now(timezone(time_zone)).strftime(time_format)}")
    logger.info(
        "---------------------------------------------------------------------------------------------")

    while True:
        timing = dt.now(timezone(time_zone))
        print("-----------------------------------------")
        print(f'Time: {timing.strftime(time_format)}')

        res = timing.minute % interval

        if res == 1 and is_trading_time(timing):
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
            time.sleep(interval * 60)
        else:
            res = 5 if res == 0 else res
            sleep_time = interval - res + 1
            print(f"Sleep Time: {sleep_time} min")
            time.sleep(sleep_time * 60)


logger = get_logger()
run_code()
