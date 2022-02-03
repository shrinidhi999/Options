import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_option_price(option):
    try:
        url = "https://tradingtick.com/options/longshort.php"

        payload = '{"symb":"banknifty","interval":"5","stike":"' + \
            option + '","type":"data"}'

        result = eval(requests.request("POST", url, data=payload,
                                       verify=False).json()[0].replace("null", "0"))[1]
        return float(result['lastprice'])
    except:
        return 0


if __name__ == "__main__":
    option_strike = "39300CE"
    print(get_option_price(option_strike))
