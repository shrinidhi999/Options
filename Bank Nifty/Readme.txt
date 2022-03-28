Packages to install:
pip install yfinance
pip install plyer
pip install smartapi-python
pip install websocket-client
pip install pandas_ta
pip install selenium  

Install chrome web driver. Create folder localhost inside chrome driver installed location.

Check the link for more details: https://www.youtube.com/watch?v=FVumnHy5Tzo&ab_channel=HelloWorld

Run: Nifty_strategy.py
1. Update params
2. Open cmd prompt and run following cmds: 
	a. cd C:\Program Files (x86)\Google\Chrome\Application
	b. chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chromedriver_win32\localhost"
3. Run the Nifty_strategy.bat	


Run: Nifty_grid_search.py
1. In Open_Interest.txt, add today's OI values copied from tradingtick website.
2. Uncomment the update_open_interest_data() and df = update_market_data().
3. Run unit_test() first. It will download the latest data and update the OI and corresponding cache.
4. Now comment the unit_test() and run the grid_search_code(time_zone).
5. It will give the optimized set of params for the next day.
6. Copy the optimized params to Nifty_strategy.py

