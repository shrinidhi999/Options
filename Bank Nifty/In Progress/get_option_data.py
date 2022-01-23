import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

option_url = "https://tradingtick.com/options/longshort.php"
option_strike = "36000CE"


def get_option_price(url, option):
    payload = '{"symb":"banknifty","interval":"5","stike":"' + \
        option + '","type":"data"}'

    result = eval(requests.request("POST", url, data=payload,
                                   verify=False).json()[0].replace("null", "0"))[0]

    result = float(result['lp']) + float(result['lastprice']
                                         ) if float(result['lp']) < 0 else float(result['lastprice'])
    return result


print(get_option_price(option_url, option_strike))
