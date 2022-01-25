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

present_day = (dt.now(timezone(time_zone)).today())

shift = timedelta(max(1, (present_day.weekday() + 6) % 7 - 3))
last_business_day = (present_day - shift).strftime("%Y-%m-%d")

weekly_expiry = "BANKNIFTY27JAN22"
instrument_list = None

last_business_day = "2022-01-24"

df = yf.download(symbol, start=last_business_day,
                 period="1d", interval=str(interval) + "m")
df.tail()
