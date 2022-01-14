from datetime import datetime as dt
from datetime import timedelta, time as tm
import pandas as pd

import requests

import yfinance as yf


symbol1 = "^NSEBANK"

input = "2022-01-13"

df = yf.download(symbol1, start=input, period="1d", interval="5m")


df.head(20)

is_closing_time = tm(dt.now().hour, dt.now().minute) > tm(14, 30)
