# pip install yfinance

# region imports

import math
import os
import sys

sys.path.append(os.getcwd() + r'\Bank Nifty\src\modules')   # nopep8
import time
import warnings
from datetime import datetime as dt
from datetime import time, timedelta

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from plyer import notification
from pytz import timezone
from tqdm import tqdm

from indicators import rsi, supertrend

warnings.filterwarnings("ignore")

# endregion

# region test vars

interval = 5
symbol = "^NSEBANK"

call_signal = False
put_signal = False
call_strike_price = 0
put_strike_price = 0


signal_start_time = []
signal_end_time = []
signal_type = []
signal_strike_price = []
signal_is_correct = []
signal_result_price = []

# endregion

# region strategy vars

test_start_year = 2019  # data available from 2015

rsi_period = 2
rsi_upper_limit = 95
rsi_lower_limit = 0.5
margin = 20

st1_length = 10
st1_factor = 1
st2_length = 10
st2_factor = 2
st3_length = 10
st3_factor = 3

# endregion

# region methods


def update_signal_vals(sig_time, sig_type, sig_price):
    global signal_start_time, signal_type, signal_strike_price

    signal_start_time.append(sig_time)
    signal_type.append(sig_type)
    signal_strike_price.append(sig_price)


def update_signal_result(val, is_correct):
    global signal_result_price, signal_is_correct

    signal_result_price.append(val)
    signal_is_correct.append(is_correct)


def alert(arr, timing, close_val, open_val, high_val, low_val, rsi_val):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time

    if len(signal_strike_price) > len(signal_result_price):
        if call_signal and (high_val >= (call_strike_price + margin)):
            update_signal_result(high_val, True)

        elif put_signal and (low_val <= (put_strike_price - margin)):
            update_signal_result(low_val, True)

    is_closing_time = time(timing.hour, timing.minute) >= time(14, 30)

    if timing.hour < 10 or is_closing_time:
        set_out_of_trade_vals(timing)
        return

    timing = timing.strftime("%d-%m-%Y %H:%M")

    signal_strategy(arr, timing, close_val, open_val, rsi_val)


def set_out_of_trade_vals(timing):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time

    if call_signal:
        call_signal = False
        signal_end_time.append(timing.strftime("%d-%m-%Y %H:%M"))
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(0, False)

    elif put_signal:
        put_signal = False
        signal_end_time.append(timing.strftime("%d-%m-%Y %H:%M"))
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(0, False)


def signal_strategy(arr, timing, close_val, open_val, rsi_val):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time

    if (
        arr.all()
        and call_signal == False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
    ):
        call_signal = True
        call_strike_price = close_val
        price = int(math.ceil(close_val / 100.0)) * 100
        price += 100
        update_signal_vals(timing, "CALL", close_val)

    if (
        not any(arr)
        and put_signal == False
        and close_val < open_val
        and rsi_val > rsi_lower_limit
    ):
        put_signal = True
        put_strike_price = close_val
        price = int(math.floor(close_val / 100.0)) * 100
        price -= 100
        update_signal_vals(timing, "PUT", close_val)

    if call_signal and not arr.all():
        call_signal = False
        signal_end_time.append(timing)
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(0, False)

    if put_signal and arr.any():
        put_signal = False
        signal_end_time.append(timing)
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(0, False)


def download_data():
    df = pd.read_csv(r'Bank Nifty\test data\NIFTY BANK Data.csv')
    df = df.set_index('Datetime')
    df.index = pd.to_datetime(df.index)
    df = df[df.index.year >= test_start_year]
    return df


def get_results():
    df_test_result = pd.DataFrame(
        {
            "Signal Start Time": signal_start_time,
            "Signal End Time": signal_end_time,
            "Signal Type": signal_type,
            "Current Price": signal_strike_price,
            "Resultant Price": signal_result_price,
            "Is Signal Correct": signal_is_correct,
        }
    )

    print("Sample Result:")
    results = df_test_result[df_test_result['Is Signal Correct'] == False]
    print(df_test_result.tail(10))

    print(
        f"Start year: {test_start_year} \nInterval: {interval} min \nMargin Points: {margin} \nAccuracy: {round((sum(signal_is_correct) / len(signal_is_correct) * 100), 2)}%"
    )

    rev = (sum(signal_is_correct) * 500) - \
        ((len(signal_is_correct) - sum(signal_is_correct)) * 500)
    print(f"Revenue: {rev}")


def test_code():

    # todo remove

    df = download_data()
    df["ST_7"] = supertrend(df, st1_length, st1_factor)["in_uptrend"]
    df["ST_8"] = supertrend(df, st2_length, st2_factor)["in_uptrend"]
    df["ST_9"] = supertrend(df, st3_length, st3_factor)["in_uptrend"]
    df["RSI"] = rsi(df, periods=rsi_period)

    for i in tqdm(range(len(df))):
        arr = df.iloc[i][["ST_7", "ST_8", "ST_9"]].values
        alert(
            arr,
            df.index[i],
            df["Close"][i],
            df["Open"][i],
            df["High"][i],
            df["Low"][i],
            df["RSI"][i],
        )
    get_results()


test_code()

# endregion
