import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_option_price(option):
    url = "https://tradingtick.com/options/longshort.php"

    payload = '{"symb":"banknifty","interval":"5","stike":"' + \
        option + '","type":"data"}'

    result = eval(requests.request("POST", url, data=payload,
                                   verify=False).json()[0].replace("null", "0"))[0]

    result = float(result['lp']) + float(result['lastprice']
                                         ) if float(result['lp']) < 0 else float(result['lastprice'])
    return result


if __name__ == "__main__":
    option_strike = "38200CE"
    print(get_option_price(option_strike))
