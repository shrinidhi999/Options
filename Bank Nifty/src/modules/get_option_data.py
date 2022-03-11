import json
import requests
import urllib3
import math
import os
from joblib import Memory

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def get_call_put_oi_diff_test(timing="2022-03-10 11:13"):
    try:
        minute = int(timing.split(':')[1])
        minute = math.floor(minute/5)*5

        timing = timing.replace(timing.split(':')[1], str(minute))

        response = get_oi_data_test(timing.split()[0])

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
def get_oi_data_test(date):
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


def clear_cache():
    get_oi_data_test.clear()


if __name__ == "__main__":
    # option_strike = "386000CE"
    # print(get_option_price(option_strike))

    # print(get_call_put_oi_diff())
    # print(get_call_put_oi_diff_test("2022-03-10 10:18"))
    clear_cache()
