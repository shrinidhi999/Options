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

import pandas as pd
import pandas_ta as ta
import yfinance as yf
from indicators import rsi, supertrend
from pytz import timezone

warnings.filterwarnings("ignore")

# endregion

# region test vars

interval = 5
symbol = "^NSEBANK"

input = (dt.now(timezone("Asia/Kolkata")).today() -
         timedelta(days=59)).strftime("%Y-%m-%d")
# input = "2022-02-01"

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
# (10, 1.2, 7, 2.4, 9, 3.6, 5, 95, 0.05, 14, 150) - 84% - 102
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

bb_width_min = 150
ema_length = 14
rsi_period = 5
rsi_upper_limit = 95
rsi_lower_limit = 0.05
margin = 10

st1_length = 10
st1_factor = 1.2
st2_length = 7
st2_factor = 2.4
st3_length = 9
st3_factor = 3.6

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


def alert(arr, timing, close_val, open_val, high_val, low_val, rsi_val, ema_val, bb_width):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time

    # print(timing, close_val, open_val, high_val, low_val, rsi_val, ema_val)

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
    signal_strategy(arr, timing, close_val, open_val,
                    rsi_val, high_val, low_val, ema_val, bb_width)


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


def signal_strategy(arr, timing, close_val, open_val, rsi_val, high_val, low_val, ema_val, bb_width):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time

    if (
        bb_width > bb_width_min
        and arr.all()
        and call_signal == False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
        and low_val > ema_val
    ):
        call_signal = True
        call_strike_price = high_val
        price = int(math.ceil(high_val / 100.0)) * 100
        price += 100
        update_signal_vals(timing, "CALL", high_val)

    if (
        bb_width > bb_width_min
        and not any(arr)
        and put_signal == False
        and close_val < open_val
        and rsi_val > rsi_lower_limit
        and high_val < ema_val
    ):
        put_signal = True
        put_strike_price = low_val
        price = int(math.floor(low_val / 100.0)) * 100
        price -= 100
        update_signal_vals(timing, "PUT", low_val)

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
    df = None
    try:
        df = yf.download(symbol, start=input,
                         period="1d", interval=str(interval) + "m")

    except Exception as e:
        print(e.message)
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
    # df_test_result = df_test_result[df_test_result["Is Signal Correct"] == False]
    print(df_test_result.tail(30))

    print(
        f"Interval: {interval} min \nMargin Points: {margin} \nAccuracy: {round((sum(signal_is_correct) / len(signal_is_correct) * 100), 2)}%"
    )


def test_code():

    # todo remove

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

    for i in range(len(df)):
        arr = df.iloc[i][["ST_7", "ST_8", "ST_9"]].values
        alert(
            arr,
            df.index[i],
            df["Close"][i],
            df["Open"][i],
            df["High"][i],
            df["Low"][i],
            df["RSI"][i],
            df["EMA"][i],
            df["Bollinger_Width"][i],
        )
    get_results()


test_code()

# endregion
