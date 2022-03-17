import time
from lib2to3.pgen2 import driver

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

driver = None


def get_web_driver():
    global driver

    url = "https://tradingtick.com/options/callvsput"
    driver = webdriver.Chrome(r'C:\chromedriver_win32\chromedriver')
    driver.get(url)


def get_oi_data():
    global driver

    try:
        driver.refresh()
        html = driver.page_source

        soup = BeautifulSoup(html, "html.parser")

        oi_divs = soup.find(
            'g', {'class': 'apexcharts-bar-series apexcharts-plot-series'})
        paths = oi_divs.find_all('path')

        return {'call_oi': paths[0].get('val'), 'put_oi': paths[1].get('val')}

    except Exception as e:
        print(e)
        return {'call_oi': 0, 'put_oi': 0}


def close_driver():
    driver.close()


if __name__ == '__main__':
    get_web_driver()
    print(get_oi_data())
    close_driver()
