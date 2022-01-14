# pip install yfinance

# pip install plyer


import math
import time
import warnings
from datetime import datetime as dt
from datetime import time as dtm
from datetime import timedelta

import pandas as pd
import requests
import yfinance as yf
from plyer import notification

warnings.filterwarnings("ignore")


interval = 5
symbol = "^NSEBANK"

input = (dt.today() - timedelta(days=1)).strftime("%Y-%m-%d")
# input = "2022-01-14"

call_signal = False
put_signal = False

title = "ALERT!"
token = "5013995887:AAHUu6qsNzw1Bsbq46LThezZBxbGn-E12Tw"
url = f"https://api.telegram.org/bot{token}"


rsi_upper_limit = 95
rsi_lower_limit = 0.5


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

    if ema == True:
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
    result = requests.get(url + "/sendMessage", params=params, verify=False)


def is_trading_time():
    global call_signal, put_signal

    timing = dt.now()
    is_closing_time = dtm(timing.hour, timing.minute) >= dtm(14, 30)

    if timing.hour < 10 or is_closing_time:
        if call_signal:
            call_signal = False
            print(
                f"Warning: Time Out \nCALL Exit: {timing.strftime('%d-%m-%Y %H:%M')}")

        elif put_signal:
            put_signal = False
            print(
                f"Warning: Time Out \nPUT Exit: {timing.strftime('%d-%m-%Y %H:%M')}")

        else:
            print("Out of trade timings")
        return False
    else:
        return True


def alert(super_trend_arr, super_trend_arr_old, timing, close_val, open_val, rsi_val):
    global call_signal, put_signal

    print(f"Time: {timing}")
    timing = timing.strftime("%d-%m-%Y %H:%M")
    msg = None

    # print(f"super_trend_arr: {super_trend_arr}")
    # print(f"super_trend_arr_old: {super_trend_arr_old}")
    # print(f"rsi_val: {rsi_val}")
    # print(f"close_val: {close_val}")
    # print(f"open_val: {open_val}")

    if (
        super_trend_arr.all()
        and call_signal == False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
    ):
        call_signal = True
        price = int(math.ceil(close_val / 100.0)) * 100
        price += 200

        if super_trend_arr_old.all():
            msg = f"On going CALL SIGNAL !!! {timing},  \nCALL Strike Price: {price} CE"
        else:
            msg = f"CALL SIGNAL !!! {timing},  \nCALL Strike Price: {price} CE"
        set_notification(msg)
        print(msg)

    if (
        not any(super_trend_arr)
        and put_signal == False
        and close_val < open_val
        and rsi_val > rsi_lower_limit
    ):
        put_signal = True
        price = int(math.floor(close_val / 100.0)) * 100
        price -= 200

        if not any(super_trend_arr_old):
            msg = f"On going PUT SIGNAL !!! {timing}, \nPUT Strike Price: {price} PE"
        else:
            msg = f"PUT SIGNAL !!! {timing}, \nPUT Strike Price: {price} PE"
        set_notification(msg)
        print(msg)

    if call_signal and not super_trend_arr.all():
        call_signal = False
        msg = f"CALL EXIT !!! {timing}"
        set_notification(msg)
        print(msg)

    if put_signal and super_trend_arr.any():
        put_signal = False
        msg = f"PUT EXIT !!! {timing}"
        set_notification(msg)
        print(msg)


def download_data():
    end_time = dt.now() + timedelta(minutes=1)
    return yf.download(symbol, start=input, end=end_time, period="1d", interval=str(interval) + "m")


def run_code():

    while True:
        print("-----------------------------------------")
        print(f'Time: {time.strftime("%d-%m-%Y %H:%M")}')
        start_time = dt.now().minute
        res = start_time % interval

        if res == 0 and is_trading_time():
            df = download_data()
            df["ST_7"] = supertrend(df, 7, 1)["in_uptrend"]
            df["ST_8"] = supertrend(df, 8, 2)["in_uptrend"]
            df["ST_9"] = supertrend(df, 9, 3)["in_uptrend"]
            df["RSI"] = rsi(df)

            super_trend_arr = df.iloc[-1][["ST_7", "ST_8", "ST_9"]].values
            super_trend_arr_old = df.iloc[-2][["ST_7", "ST_8", "ST_9"]].values

            alert(
                super_trend_arr,
                super_trend_arr_old,
                df.index[-1],
                df["Close"][-2],
                df["Open"][-2],
                df["RSI"][-2],
            )
            time.sleep(interval * 60)
        else:
            sleep_time = interval - res
            print(f"Sleep Time: {sleep_time} min")
            time.sleep(sleep_time * 60)


run_code()
