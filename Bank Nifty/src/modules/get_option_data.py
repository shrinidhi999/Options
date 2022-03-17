import json
import math
import os
from datetime import datetime as dt
import re

import pandas as pd
import requests
import urllib3
from dateutil import tz
from joblib import Memory

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


to_zone = tz.gettz('UTC')
from_zone = tz.gettz("Asia/Kolkata")

cache_dir = os.getcwd()
mem = Memory(cache_dir)


def get_option_price(option):
    try:
        url = "https://tradingtick.com/options/longshort.php"

        payload = '{"symb":"banknifty","interval":"5","stike":"' + \
            option + '","type":"data"}'

        result = eval(requests.request("POST", url, data=payload,
                                       verify=False).json()[0].replace("null", "0"))[1]
        return float(result['lastprice'])
    except Exception as e:
        print("Inside get_option_price: ", e)
        return 0


def get_call_put_oi_diff():
    try:
        url = "https://tradingtick.com/data/options"

        payload = "{\"inst\":\"NIFTY\",\"historical\":false,\"date\":null}"
        headers = {
            'content-type': "application/json",
        }

        response = requests.request(
            "POST", url, data=payload, headers=headers, verify=False)
        res = eval(response.text)

        ce_ending = []
        pe_ending = []
        ce_opening = []
        pe_opening = []

        last_traded_time = res[-1][0]
        first_traded_time = res[0][0]

        for r in res:
            if (first_traded_time) in r:
                if ("CE") in r[2]:
                    ce_opening.append(r)
                else:
                    pe_opening.append(r)

            elif (last_traded_time) in r:
                if ("CE") in r[2]:
                    ce_ending.append(r)
                else:
                    pe_ending.append(r)

        pe_opening = [p[4] for p in pe_opening]
        ce_opening = [p[4] for p in ce_opening]

        sum_ce_opening = sum(ce_opening)
        sum_pe_opening = sum(pe_opening)

        pe_ending = [p[4] for p in pe_ending]
        ce_ending = [p[4] for p in ce_ending]

        sum_ce_ending = sum(ce_ending)
        sum_pe_ending = sum(pe_ending)

        return {'call_oi': sum_ce_ending - sum_ce_opening, 'put_oi': sum_pe_ending - sum_pe_opening}

    except Exception as e:
        print("Inside get_call_put_oi_diff: ", e)
        return {'call_oi': 0, 'put_oi': 0}


def get_call_put_oi_diff_test(timing):
    try:
        minute = int(timing.split(':')[1])
        minute = str(math.floor(minute/5)*5).zfill(2)

        timing = f"{timing.split(':')[0]}:{minute}"

        response = get_oi_data_test(timing.split()[0])

        if response.empty:
            return {'call_oi': 0, 'put_oi': 0}

        ce_ending = []
        pe_ending = []
        ce_opening = []
        pe_opening = []

        trade_time = dt.strptime(timing, '%Y-%m-%d %H:%M').replace(tzinfo=from_zone).astimezone(
            to_zone).strftime('%Y-%m-%dT%H:%M')
        trade_time_check = f"{trade_time}:02.000Z"

        first_traded_time = response['date'][0]

        response = response[response['date'] <= trade_time_check]
        response = response.to_dict('records')

        for row in response:
            if (first_traded_time) in row['date']:
                if ("CE") in row['strike']:
                    ce_opening.append(row['oi'])
                else:
                    pe_opening.append(row['oi'])

            elif (trade_time) in row['date']:
                if ("CE") in row['strike']:
                    ce_ending.append(row['oi'])
                else:
                    pe_ending.append(row['oi'])

        sum_ce_opening = sum(ce_opening)
        sum_pe_opening = sum(pe_opening)

        sum_ce_ending = sum(ce_ending)
        sum_pe_ending = sum(pe_ending)

        return {'call_oi': sum_ce_ending - sum_ce_opening, 'put_oi': sum_pe_ending - sum_pe_opening}

    except Exception as e:
        print("Inside get_call_put_oi_diff_test: ", e)
        return {'call_oi': 0, 'put_oi': 0}


def test_time(timing):
    print(f"inside: {timing}")


@mem.cache(verbose=0)
def get_oi_data_test(date):
    try:
        print(f"get_oi_data_test: {date}")
        oi_data = pd.read_excel(r'Bank Nifty\test data\Open_Interest.xlsx')
        oi_data = oi_data[oi_data['date'].str.contains(
            date)].reset_index(drop=True)
        return oi_data
    except Exception as e:
        print("Inside get_oi_data_test: ", e)
        return None


def clear_cache():
    mem.clear(warn=False)


def get_call_put_oi_diff_old():
    try:
        url = "https://tradingtick.com/options/callvsput.php"

        payload = json.dumps({
            "underlying": "NIFTY",
            "range": False,
            "startStrike": "",
            "endStrike": "",
            "dataType": "latest",
            "hDate": "",
            "type": "data"
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request(
            "POST", url, headers=headers, data=payload, verify=False)

        call_put_oi = eval(eval(response.text)[0])
        call_oi = int(call_put_oi[1]['y']) - int(call_put_oi[0]['y'])
        put_oi = int(call_put_oi[3]['y']) - int(call_put_oi[2]['y'])
        return {'call_oi': call_oi, 'put_oi': put_oi}

    except Exception as e:
        print("Inside get_call_put_oi_diff: ", e)
        return {'call_oi': 0, 'put_oi': 0}


def get_call_put_oi_diff_test_old(timing="2022-03-10 11:13"):
    try:
        minute = int(timing.split(':')[1])
        minute = math.floor(minute/5)*5

        timing = timing.replace(timing.split(':')[1], str(minute))

        response = get_oi_data_test_old(timing.split()[0])

        opening_oi = eval(eval(response.text)[0])
        call_put_oi = eval(eval(response.text)[1])
        call_oi = put_oi = 0

        for oi_dict in call_put_oi:
            if oi_dict['x'] == timing:
                if oi_dict['type'] == 'CE':
                    call_oi = int(oi_dict['y']) - int(opening_oi[0]['y'])
                elif oi_dict['type'] == 'PE':
                    put_oi = int(oi_dict['y']) - int(opening_oi[2]['y'])

        return {'call_oi': call_oi, 'put_oi': put_oi}

    except Exception as e:
        print("Inside get_call_put_oi_diff_test: ", e)
        return {'call_oi': 0, 'put_oi': 0}


@mem.cache(verbose=0)
def get_oi_data_test_old(date):
    try:
        url = "https://tradingtick.com/options/callvsput.php"

        payload = json.dumps({"underlying": "NIFTY", "range": False, "startStrike": "",
                              "endStrike": "", "dataType": "hist", "hDate": date, "type": "data"})
        headers = {
            'Content-Type': 'application/json'
        }

        return requests.request(
            "POST", url, headers=headers, data=payload, verify=False)

    except Exception as e:
        print("Inside get_oi_data_test: ", e)
        return None


if __name__ == "__main__":
    # option_strike = "386000CE"
    # print(get_option_price(option_strike))
    # get_oi_historic_data()
    # print(get_call_put_oi_diff())

    # {'call_oi': 22043350, 'put_oi': 27898700}
    # print(get_call_put_oi_diff_test("2022-03-10 10:18"))

    # get_call_put_oi_diff_old()
    clear_cache()
