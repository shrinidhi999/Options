# pip install yfinance

# region imports

import math
import os
import sys
import itertools
import multiprocessing
from multiprocessing import Pool


sys.path.append(os.getcwd() + r'\Bank Nifty\src\modules')   # nopep8
import time
import warnings
from datetime import datetime as dt
from datetime import time, timedelta

import numpy as np
import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf
from plyer import notification
from pytz import timezone
from tqdm import tqdm

from indicators import rsi, supertrend, atr

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
signal_loss = []
signal_profit = []

today = None
loss_day = None
# endregion

# region strategy vars

test_start_year = 2019  # data available from 2015

ema_length = 9
rsi_period = 5
rsi_upper_limit = 95
rsi_lower_limit = 0.05
margin = 10
stoploss = 1
stoploss_factor = 1
atr_period = 10
bb_width_min = 250

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

# diff - used when this method is called when timeout happens


def update_signal_result(val, is_correct, diff_in_pts=None):
    global signal_result_price, signal_is_correct, signal_loss, signal_profit, loss_day

    signal_result_price.append(val)
    signal_is_correct.append(is_correct)

    if is_correct:
        signal_profit.append(25 * margin)
    else:
        loss_day = today
        if diff_in_pts:
            signal_loss.append(25 * diff_in_pts)
        else:
            signal_loss.append(25 * stoploss)


def alert(arr, timing, close_val, open_val, high_val, low_val, rsi_val, ema_val, bb_width, atr_val):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time

    if len(signal_strike_price) > len(signal_result_price):
        if call_signal:
            if (low_val <= (call_strike_price - stoploss)):
                update_signal_result(low_val, False)

            elif (high_val >= (call_strike_price + margin)):
                update_signal_result(high_val, True)

        elif put_signal:
            if (high_val >= (put_strike_price + stoploss)):
                update_signal_result(high_val, False)

            elif (low_val <= (put_strike_price - margin)):
                update_signal_result(low_val, True)

    is_closing_time = time(timing.hour, timing.minute) >= time(13, 00)

    if timing.hour < 10 or is_closing_time:
        set_out_of_trade_vals(timing, high_val, low_val)
        return

    timing = timing.strftime("%d-%m-%Y %H:%M")

    signal_strategy(arr, timing, close_val, open_val,
                    rsi_val, high_val, low_val, ema_val, bb_width, atr_val)


def set_out_of_trade_vals(timing, high_val, low_val):
    global call_signal, put_signal, signal_end_time

    if call_signal:
        call_signal = False
        signal_end_time.append(timing.strftime("%d-%m-%Y %H:%M"))
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(low_val, False, call_strike_price - low_val)

    elif put_signal:
        put_signal = False
        signal_end_time.append(timing.strftime("%d-%m-%Y %H:%M"))
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(high_val, False, high_val - put_strike_price)


def signal_strategy(arr, timing, close_val, open_val, rsi_val,  high_val, low_val, ema_val, bb_width, atr_val):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time, stoploss, margin

    if (
        bb_width > bb_width_min
        and arr.all()
        and call_signal == False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
        and low_val > ema_val
    ):
        call_signal = True
        stoploss = atr_val * stoploss_factor
        # print(f"stoploss: {stoploss}")
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
        stoploss = atr_val * stoploss_factor
        # print(f"stoploss: {stoploss}")
        put_strike_price = low_val
        price = int(math.floor(low_val / 100.0)) * 100
        price -= 100
        update_signal_vals(timing, "PUT", low_val)

    if call_signal and (not arr.all() or (open_val < ema_val)):
        call_signal = False
        signal_end_time.append(timing)
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(low_val, False, call_strike_price - low_val)

    if put_signal and (arr.any() or (open_val > ema_val)):
        put_signal = False
        signal_end_time.append(timing)
        if len(signal_strike_price) > len(signal_result_price):
            update_signal_result(high_val, False, high_val - put_strike_price)


def download_data():

    df = pd.read_csv(r'Bank Nifty\test data\NIFTY BANK Data.csv')
    df = df.set_index('Datetime')
    df.index = pd.to_datetime(df.index)
    # df = df[df.index.year >= test_start_year]
    df = df[df.index > '2022-01-16 09:15:00+05:30']
    df = df[df.index.minute % interval == 0]
    return df


def get_results():
    print(len(signal_start_time))
    print(len(signal_end_time))
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

    accuracy = round(
        (sum(signal_is_correct) / len(signal_is_correct) * 100), 2)
    print("Sample Result:")
    results = df_test_result[df_test_result['Is Signal Correct'] == False]
    print(df_test_result.tail(10))

    print(
        f"Start year: {test_start_year} \nInterval: {interval} min \nMargin Points: {margin} \nAccuracy: {accuracy}%"
    )

    rev = sum(signal_profit) - sum(signal_loss)
    print(f"Revenue: {rev}")
    return accuracy, len(signal_is_correct), rev


def test_code(params):
    global st1_length, st1_factor, st2_length, st2_factor, st3_length, st3_factor, rsi_period, rsi_upper_limit, rsi_lower_limit, ema_length, bb_width_min, call_signal, put_signal, call_strike_price, put_strike_price, signal_start_time, signal_end_time, signal_type, signal_strike_price, signal_result_price, signal_is_correct, margin, stoploss_factor, signal_loss, signal_profit, atr_period, interval, today

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
    signal_loss = []
    signal_profit = []
    # todo remove

    df = download_data()
    df["ST_7"] = supertrend(df, st1_length, st1_factor)["in_uptrend"]
    df["ST_8"] = supertrend(df, st2_length, st2_factor)["in_uptrend"]
    df["ST_9"] = supertrend(df, st3_length, st3_factor)["in_uptrend"]
    df["ATR"] = atr(df, atr_period)
    df["RSI"] = rsi(df, periods=rsi_period)
    df["EMA"] = ta.ema(df["Close"], length=ema_length)
    bollinger_band = ta.bbands(df["Close"], length=20, std=2)[
        ["BBL_20_2.0", "BBU_20_2.0"]]
    df["Bollinger_Width"] = bollinger_band["BBU_20_2.0"] - \
        bollinger_band["BBL_20_2.0"]

    for i in tqdm(range(len(df))):
        today = dt.date(df.index[i])
        # if loss_day == today:
        #     continue
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
            df["ATR"][i]
        )

    return get_results()


# Margin Points: 20, Accuracy: 82.98%, Rev: 6.2K
# Margin Points: 10, Accuracy: 93.62%, Rev: 4.1K
# params = (7, 1.2, 10, 2.4, 9, 3, 5, 95, 0.05, 8, 150, 10, 1, 14, 5)
# acc, pts, rev = test_code(params)

# endregion

# region grid search

accs = None
pts_list = None
revs = None
results = []
cnt = 0

if __name__ == '__main__':

    # (7, 1.2, 10, 2.4, 9, 3, 5, 95, 0.05, 8, 150, 10, 1, 8, 5)
    # initialize lists
    st1_length_list = [7]
    st1_factor_list = [1]
    st2_length_list = [8]
    st2_factor_list = [2.4]
    st3_length_list = [9]
    st3_factor_list = [3]
    rsi_period_list = [5]
    rsi_upper_limit_list = [95]
    rsi_lower_limit_list = [0.05]
    ema_length_list = [8]
    bb_width = [150]
    margin = [10, 20]
    stoploss_factor = [1]
    atr_period = [2]
    interval = [5]

    final = [st1_length_list, st1_factor_list, st2_length_list, st2_factor_list, st3_length_list,
             st3_factor_list, rsi_period_list, rsi_upper_limit_list, rsi_lower_limit_list, ema_length_list, bb_width, margin, stoploss_factor, atr_period, interval]
    res_combos = list(itertools.product(*final))

    with Pool(multiprocessing.cpu_count() - 2) as p:
        results.extend(
            iter(tqdm(p.map(test_code, res_combos), total=len(res_combos))))

    accs = [i[0] for i in results]
    pts_list = [i[1] for i in results]
    revs = [i[2] for i in results]

    print(f"Max Accuracy: {max(accs)}")
    print(f"Max accuracy combination: {res_combos[accs.index(max(accs))]}")

    # print(f"Max Signals generated: {max(pts_list)}")
    # print(f"Max Signals Index: {pts_list.index(max(pts_list))}")

    print(f"Max Profit: {max(revs)}")
    print(f"Max Profit combination: {res_combos[revs.index(max(revs))]}")

    print(accs)
    print(revs)

# endregion
