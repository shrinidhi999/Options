import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://tradingtick.com/options/longshort.php"
option = "36000PE"

payload = '{"symb":"banknifty","interval":"5","stike":"' + \
    option + '","type":"data"}'

result = eval(requests.request("POST", url, data=payload,
                               verify=False).json()[0].replace("null", "0"))[0]


result = float(result['lp']) + float(result['lastprice']
                                     ) if float(result['lp']) < 0 else float(result['lastprice'])
print(result)
