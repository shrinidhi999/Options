# pip install yfinance

# region imports
import itertools
import math
import multiprocessing
import os
import sys
from datetime import datetime as dt
from datetime import timedelta
from multiprocessing import Pool

from pytz import timezone

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
from indicators import atr, rsi, supertrend
from pandas.tseries.offsets import BDay
from pytz import timezone
from tqdm import tqdm

warnings.filterwarnings("ignore")

# endregion

# region test vars

time_zone = "Asia/Kolkata"
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


def alert(arr, timing, close_val, open_val, high_val, low_val, rsi_val, ema_val, bb_width, atr_val, prev_close, prev_open):
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
                    rsi_val, high_val, low_val, ema_val, bb_width, atr_val, prev_close, prev_open)


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


def signal_strategy(arr, timing, close_val, open_val, rsi_val,  high_val, low_val, ema_val, bb_width, atr_val, prev_close, prev_open):
    global call_signal, put_signal, call_strike_price, put_strike_price, signal_end_time, stoploss, margin

    if (
        bb_width > bb_width_min
        and arr.all()
        and call_signal == False
        and close_val > open_val
        and rsi_val < rsi_upper_limit
        and low_val > ema_val
        and open_val > prev_close
        and open_val > prev_open
    ):
        call_signal = True
        # stoploss = atr_val * stoploss_factor
        stoploss = stoploss_factor
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
        and open_val < prev_close
        and open_val < prev_open
    ):
        put_signal = True
        # stoploss = atr_val * stoploss_factor
        stoploss = stoploss_factor
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


def download_data(business_day=None):

    df = pd.read_csv(r'Bank Nifty\test data\NIFTY BANK Data.csv')
    df = df.set_index('Datetime')
    df.index = pd.to_datetime(df.index)

    if business_day:
        df = df[df.index >= business_day]
        # df = df[df.index >= '2021-12-07']
        # df = df[df.index <= '2021-12-16']
    else:
        df = df[df.index.year >= test_start_year]

    df = df[df.index.minute % interval == 0]
    return df


def get_results(business_day=None):
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
    print(df_test_result.tail(30))

    date_msg = f"Start Date: {business_day}" if business_day else f"Start year: {test_start_year}"
    print(
        f"{date_msg} \nInterval: {interval} min \nMargin Points: {margin} \nAccuracy: {accuracy}%"
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
    business_day = params[15]

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

    df = download_data(business_day)
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
            df["ATR"][i],
            df["Close"][i-1],
            df["Open"][i-1]
        )

    return get_results(business_day)


def update_test_data(df=None):
    input = (dt.now(timezone("Asia/Kolkata")).today() -
             timedelta(days=59)).strftime("%Y-%m-%d")

    if not df:
        df = yf.download(symbol, start=input,
                         period="1d", interval=str(interval) + "m")

    df_test_data = pd.read_csv(
        r'D:\Options\Bank Nifty\test data\NIFTY BANK Data.csv')

    df['Datetime'] = df.index
    df.reset_index(drop=True, inplace=True)

    df_latest = df[df.Datetime > pd.Timestamp(
        df_test_data.Datetime.iloc[-1])]
    df_test_data = df_test_data.append(df_latest)
    df_test_data = df_test_data[['Datetime', 'Open',
                                 'High', 'Low',	'Close', 'Adj Close', 'Volume']]
    df_test_data.to_csv(
        r'D:\Options\Bank Nifty\test data\NIFTY BANK Data.csv', index=False)


def unit_test():
    weekly_business_day = (dt.today() - BDay(6)).strftime("%Y-%m-%d")

    # Go to last 7 business days
    params = (7, 1, 8, 2, 9, 3, 5, 95, 0.05, 8,
              125,10, 40, 2, 5, weekly_business_day)
    # update_test_data()
    return test_code(params)

# endregion

# region grid search


def grid_search_code(time_zone):

    # (7, 1.2, 10, 2.4, 9, 3, 5, 95, 0.05, 8, 125, 10, 2, 2, 5)

    accs = None
    pts_list = None
    revs = None
    results = []
    cnt = 0

    # update_test_data()

    # last 6th business day
    weekly_business_day = (dt.today() - BDay(6)).strftime("%Y-%m-%d")

    # initialize lists
    st1_length_list = [7, 10]
    st1_factor_list = [1, 1.2]
    st2_length_list = [8, 10]
    st2_factor_list = [2, 2.4]
    st3_length_list = [9, 10]
    st3_factor_list = [3, 3.6]
    rsi_period_list = [5]
    rsi_upper_limit_list = [95]
    rsi_lower_limit_list = [0.05]
    ema_length_list = [8, 9, 14]
    bb_width = [125, 150]
    margin = [10, 20]
    stoploss_factor = [20, 30, 40]
    # atr_period = [2, 9]
    atr_period = [2]
    interval = [5]
    business_day = [weekly_business_day]

    final = [st1_length_list, st1_factor_list, st2_length_list, st2_factor_list, st3_length_list,
             st3_factor_list, rsi_period_list, rsi_upper_limit_list, rsi_lower_limit_list, ema_length_list, bb_width, margin, stoploss_factor, atr_period, interval, business_day]
    res_combos = list(itertools.product(*final))

    with Pool(multiprocessing.cpu_count() - 1) as p:
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

    # print(accs)
    # print(revs)
    # print(pts_list)

# endregion


if __name__ == '__main__':

    # grid_search_code(time_zone)

    acc, pts, rev = unit_test()
