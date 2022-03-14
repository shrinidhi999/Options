import json
import math
import os
from datetime import datetime as dt

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
        print(e)
        return 0


def get_call_put_oi_diff():
    try:
        url = "https://api.tradingtick.com/api/data/options"

        payload = "{\"inst\":\"NIFTY\",\"historical\":false,\"date\":null}"
        headers = {
            'content-type': "application/json",
        }

        response = requests.request("POST", url, data=payload, headers=headers)
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
        print(e)
        return {'call_oi': 0, 'put_oi': 0}


def get_call_put_oi_diff_oi_tracker():
    try:
        url = "https://api.oitracker.com/graph/callVsPut"

        querystring = {"tickerType": "NIFTY",
                       "interval": "5", "type": "1", "expiry": "1"}

        payload = "{\"ceTicker\":[\"NIFTY2231715900CE\",\"NIFTY2231715950CE\",\"NIFTY2231716000CE\",\"NIFTY2231716050CE\",\"NIFTY2231716100CE\",\"NIFTY2231716150CE\",\"NIFTY2231716200CE\",\"NIFTY2231716250CE\",\"NIFTY2231716300CE\",\"NIFTY2231716350CE\",\"NIFTY2231716400CE\",\"NIFTY2231716450CE\",\"NIFTY2231716500CE\",\"NIFTY2231716550CE\",\"NIFTY2231716600CE\",\"NIFTY2231716650CE\",\"NIFTY2231716700CE\",\"NIFTY2231716750CE\",\"NIFTY2231716800CE\",\"NIFTY2231716850CE\",\"NIFTY2231716900CE\",\"NIFTY2231716950CE\",\"NIFTY2231717000CE\",\"NIFTY2231717050CE\",\"NIFTY2231717100CE\",\"NIFTY2231717150CE\",\"NIFTY2231717200CE\",\"NIFTY2231717250CE\",\"NIFTY2231717300CE\",\"NIFTY2231717350CE\",\"NIFTY2231717400CE\"],\"peTicker\":[\"NIFTY2231715900PE\",\"NIFTY2231715950PE\",\"NIFTY2231716000PE\",\"NIFTY2231716050PE\",\"NIFTY2231716100PE\",\"NIFTY2231716150PE\",\"NIFTY2231716200PE\",\"NIFTY2231716250PE\",\"NIFTY2231716300PE\",\"NIFTY2231716350PE\",\"NIFTY2231716400PE\",\"NIFTY2231716450PE\",\"NIFTY2231716500PE\",\"NIFTY2231716550PE\",\"NIFTY2231716600PE\",\"NIFTY2231716650PE\",\"NIFTY2231716700PE\",\"NIFTY2231716750PE\",\"NIFTY2231716800PE\",\"NIFTY2231716850PE\",\"NIFTY2231716900PE\",\"NIFTY2231716950PE\",\"NIFTY2231717000PE\",\"NIFTY2231717050PE\",\"NIFTY2231717100PE\",\"NIFTY2231717150PE\",\"NIFTY2231717200PE\",\"NIFTY2231717250PE\",\"NIFTY2231717300PE\",\"NIFTY2231717350PE\",\"NIFTY2231717400PE\"]}"
        headers = {
            'content-type': "application/json",
            'authorization': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjYyMmQ5NTJmOGFlMTc5NjY5NWFjOWM3MSIsInBob25lTnVtYmVyIjoiODEyMzU1OTc4MiIsImVtYWlsIjoic2hyaW5pZGhpLnJtOTBAZ21haWwuY29tIiwidXNlclR5cGUiOiJmcmVlVXNlciIsImRldmljZUluZm8iOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvOTkuMC40ODQ0LjUxIFNhZmFyaS81MzcuMzYiLCJpYXQiOjE2NDcxNTQ0OTgsImV4cCI6MTY0NzI0MDg5OH0.pEYSlvn69JV7UnTDCX1rX5RicGvramHXFqJb-8Q39wE",
            'cache-control': "no-cache",
            'postman-token': "ab57d7fb-b79e-0e9f-aff2-4b7195c9fba8"
        }

        response = requests.request(
            "POST", url, data=payload, headers=headers, params=querystring)
        response = response.text.replace('true', 'True')
        result = eval(response)

        return {'call_oi': result['result']['data'][-1]['callOi'], 'put_oi': result['result']['data'][-1]['putOi'], 'oi_diff': result['result']['data'][-1]['result']}
    except Exception as e:
        print(e)
        return {'call_oi': 0, 'put_oi': 0, 'oi_diff': 0}


def get_call_put_oi_diff_test(timing):
    try:
        print("inside")
        print(timing)
        minute = int(timing.split(':')[1])
        minute = math.floor(minute/5)*5

        timing = timing.replace(timing.split(':')[1], str(minute))

        response = get_oi_data_test(timing.split()[0])
        res = eval(response.text)

        ce_ending = []
        pe_ending = []
        ce_opening = []
        pe_opening = []

        trade_time = dt.strptime(timing, '%Y-%m-%d %H:%M').replace(tzinfo=from_zone).astimezone(
            to_zone).strftime('%Y-%m-%dT%H:%M')

        first_traded_time = res[0][0]

        for r in res:
            if (first_traded_time) in r[0]:
                if ("CE") in r[2]:
                    ce_opening.append(r)
                else:
                    pe_opening.append(r)

            elif (trade_time) in r[0]:
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
        print(e)
        return {'call_oi': 0, 'put_oi': 0}


def test_time(timing):
    print(f"inside: {timing}")


@mem.cache(verbose=0)
def get_oi_data_test(date):
    try:
        url = "https://api.tradingtick.com/api/data/options"

        payload = json.dumps(
            {"inst": "NIFTY", "historical": True, "date": date})
        headers = {
            'Content-Type': 'application/json'
        }

        return requests.request(
            "POST", url, headers=headers, data=payload, verify=False)

    except Exception as e:
        print(e)
        return None


def clear_cache():
    mem.clear(warn=False)


def get_oi_historic_data():
    try:
        url = "https://api.oitracker.com/graph/callVsPut"

        querystring = {"tickerType": "NIFTY",
                       "interval": "5", "type": "1", "expiry": "1"}

        payload = "{\"ceTicker\":[\"NIFTY2231715900CE\",\"NIFTY2231715950CE\",\"NIFTY2231716000CE\",\"NIFTY2231716050CE\",\"NIFTY2231716100CE\",\"NIFTY2231716150CE\",\"NIFTY2231716200CE\",\"NIFTY2231716250CE\",\"NIFTY2231716300CE\",\"NIFTY2231716350CE\",\"NIFTY2231716400CE\",\"NIFTY2231716450CE\",\"NIFTY2231716500CE\",\"NIFTY2231716550CE\",\"NIFTY2231716600CE\",\"NIFTY2231716650CE\",\"NIFTY2231716700CE\",\"NIFTY2231716750CE\",\"NIFTY2231716800CE\",\"NIFTY2231716850CE\",\"NIFTY2231716900CE\",\"NIFTY2231716950CE\",\"NIFTY2231717000CE\",\"NIFTY2231717050CE\",\"NIFTY2231717100CE\",\"NIFTY2231717150CE\",\"NIFTY2231717200CE\",\"NIFTY2231717250CE\",\"NIFTY2231717300CE\",\"NIFTY2231717350CE\",\"NIFTY2231717400CE\"],\"peTicker\":[\"NIFTY2231715900PE\",\"NIFTY2231715950PE\",\"NIFTY2231716000PE\",\"NIFTY2231716050PE\",\"NIFTY2231716100PE\",\"NIFTY2231716150PE\",\"NIFTY2231716200PE\",\"NIFTY2231716250PE\",\"NIFTY2231716300PE\",\"NIFTY2231716350PE\",\"NIFTY2231716400PE\",\"NIFTY2231716450PE\",\"NIFTY2231716500PE\",\"NIFTY2231716550PE\",\"NIFTY2231716600PE\",\"NIFTY2231716650PE\",\"NIFTY2231716700PE\",\"NIFTY2231716750PE\",\"NIFTY2231716800PE\",\"NIFTY2231716850PE\",\"NIFTY2231716900PE\",\"NIFTY2231716950PE\",\"NIFTY2231717000PE\",\"NIFTY2231717050PE\",\"NIFTY2231717100PE\",\"NIFTY2231717150PE\",\"NIFTY2231717200PE\",\"NIFTY2231717250PE\",\"NIFTY2231717300PE\",\"NIFTY2231717350PE\",\"NIFTY2231717400PE\"]}"
        headers = {
            'content-type': "application/json",
            'authorization': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjYyMmQ5NTJmOGFlMTc5NjY5NWFjOWM3MSIsInBob25lTnVtYmVyIjoiODEyMzU1OTc4MiIsImVtYWlsIjoic2hyaW5pZGhpLnJtOTBAZ21haWwuY29tIiwidXNlclR5cGUiOiJmcmVlVXNlciIsImRldmljZUluZm8iOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvOTkuMC40ODQ0LjUxIFNhZmFyaS81MzcuMzYiLCJpYXQiOjE2NDcxNTQ0OTgsImV4cCI6MTY0NzI0MDg5OH0.pEYSlvn69JV7UnTDCX1rX5RicGvramHXFqJb-8Q39wE",
            'cache-control': "no-cache",
            'postman-token': "78a072f4-0743-8173-c90d-26db7e211640"
        }

        response = requests.request(
            "POST", url, data=payload, headers=headers, params=querystring)

        response = response.text.replace('true', 'True')
        result = eval(response)
        df = pd.DataFrame.from_records(result['result']['data'])
        # df['Expiry'] = "NIFTY17MAR22"
        # df.to_csv(f"{os.getcwd()}\Bank Nifty\\test data\OI.csv", index=False)

        df_old = pd.read_csv(f"{os.getcwd()}\Bank Nifty\\test data\OI.csv")

        pd.concat([df_old, df]).to_csv(
            f"{os.getcwd()}\Bank Nifty\\test data\OI.csv", index=False)

    except Exception as e:
        print(e)


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
        print(e)
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
        print(e)
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
        print(e)
        return None


if __name__ == "__main__":
    # option_strike = "386000CE"
    # print(get_option_price(option_strike))
    # print(get_call_put_oi_diff_oi_tracker())
    # get_oi_historic_data()
    # print(get_call_put_oi_diff())
    print(get_call_put_oi_diff_test_old("2022-03-10 10:18"))
    # get_call_put_oi_diff_old()
    # clear_cache()
