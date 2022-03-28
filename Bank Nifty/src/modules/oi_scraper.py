import time
from lib2to3.pgen2 import driver

from selenium import webdriver

driver = None
driver_location = r"C:\chromedriver_win32\chromedriver"
url = "https://tradingtick.com/options/callvsput"


def get_web_driver():
    '''
    Link to fix sign in : https://www.youtube.com/watch?v=FVumnHy5Tzo&ab_channel=HelloWorld
    cmd prompt: 
    cd C:\Program Files (x86)\Google\Chrome\Application
    chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chromedriver_win32\localhost"
    '''
    global driver

    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(driver_location, options=options)
    driver.get(url)


def get_oi_data():
    global driver

    try:
        driver.refresh()
        time.sleep(1)
        # html = driver.page_source
        call_val = driver.find_element_by_id(
            "SvgjsPath1270").get_attribute('val')
        put_val = driver.find_element_by_id(
            "SvgjsPath1272").get_attribute('val')

        return {'call_oi': int(call_val), 'put_oi': int(put_val)}

    except Exception as e:
        print(f"Get OI data failed: {e}")
        return {'call_oi': 0, 'put_oi': 0}


def close_driver():
    driver.close()


if __name__ == '__main__':
    get_web_driver()
    print(get_oi_data())
    # close_driver()
