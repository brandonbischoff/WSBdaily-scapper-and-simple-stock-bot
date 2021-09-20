import datetime
import time
import pandas as pd
import yfinance as yf
import pytz
from tzlocal import get_localzone
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
import re
import pytz

def next_market_day(time_stamp):

    tz_east = pytz.timezone('US/Eastern')
    date_added = datetime.datetime.fromtimestamp(time_stamp, tz_east)
    the_day_added = date_added.strftime("%a")
    the_time_of_day = int(date_added.strftime("%H"))

    if the_day_added == "Sat":
        time_stamp = change_timestamp(time_stamp, 2, " 09:30:00")

    elif the_day_added == "Sun":
        time_stamp = change_timestamp(time_stamp, 1, " 09:30:00")

    elif the_day_added == "Fri" and the_time_of_day > 12:
        time_stamp = change_timestamp(time_stamp, 3, " 09:30:00")

    elif the_time_of_day >= 12:
        time_stamp = change_timestamp(time_stamp, 1, " 09:30:00")

    else:
        return (time_stamp)

    return(time_stamp)


def change_timestamp(timestamp, num_days, time_day):
    """ Takes in a unix time,
        adds a specified number of days,
        and adds a specified hour,min,second.
        returns unix time                       """
    tz_east = pytz.timezone('US/Eastern')

    date = datetime.datetime.fromtimestamp(timestamp)
    end_date = date + datetime.timedelta(days=num_days)
    end_date_str = end_date.strftime("%Y-%m-%d") + time_day
    end_date_object = datetime.datetime.strptime(
        end_date_str, "%Y-%m-%d %H:%M:%S")
    date_east = tz_east.localize(end_date_object)

    end_date_timestamp = date_east.timestamp()

    return(end_date_timestamp)

def get_stocks():

    """ Scrapes WSBDaily's pennystock page, and returns
        a list of all the stock names and the source
        that they came from.                           """

    compiler = re.compile('\d+.*\d\d:\d\d')
    stock_list = []
    name = None
    markettype = None
    table_count = 0
    table_contents = {1: "Popular Reddit Pennystocks",
                      2: "Popular RobinHood Pennystocks",
                      3: "Popular Reddit Canada Pennystocks",
                      4: "Popular Wealthsimple Pennystocks",
                      5: "Reddit Pennystock Daily Plays",
                      6: "RobbinHood Daily Plays",
                      7: "Penny Scanner #1",
                      8: "Penny Scanner #1 Canada",
                      9: "Penny Scanner #2",
                      10: "Penny Scanner #2 Canada"}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'}
    wsb_pennny_url = "https://wsbdaily.com/penny/"
    response = requests.get(wsb_pennny_url, headers=headers).text
    soup = BeautifulSoup(response, "html.parser")


    tz_east = pytz.timezone('US/Eastern')
    tz_utc = pytz.timezone("UTC")



    for table in soup.find_all("table", class_="css-s8p85f enavj7y0"):
        table_count += 1
        for row in table.find_all("tr"):

            # uses regex to pick out date
            # Parses to date for datetime.timestamp()
            temp = compiler.search(soup.find_all(
                "div", class_="css-1hfls2k e1b8pdim22")[table_count - 1].get_text()).group()
            date = parse(temp)
            date_east = tz_east.localize(date)
            date_utc = date_east.replace(tzinfo =tz_utc )
            unix_east = (datetime.datetime.timestamp(date_east))
            unix_utc = (datetime.datetime.timestamp(date_utc))

            for stock_name in row.find_all("span", class_="css-1sctek8 e1b8pdim9"):
                name = stock_name.get_text()

            for market_type in row.find_all("td", class_="css-hogeaf e1b8pdim3"):
                markettype = market_type.get_text()

                if markettype != "OTC":
                    stock_list.append([name,
                                       markettype,
                                       table_contents[table_count],
                                       unix_utc])

    return(stock_list)


def update(file_name):

    """ Uses a web scrapper to get all penny stocks off
        wsbdaily.com, filters them out by when they
        were last updated on the website and updates
        the csv file.                               """

    new_stocks = get_stocks()
    df = pd.read_csv(file_name)

    filt = df["Time_Added"] == int(new_stocks[0][3])
    result = filt.any()

    if result == True:
        return(None)

    for stock in new_stocks:

        df2 = {"Name": stock[0], "Time_Added": stock[3], "Source": stock[2],"Next_Update": "New"}
        df = df.append(df2, ignore_index=True)

    df.to_csv(file_name, index=False)


def backtest(file_name,
             index,
             stock_name,
             time_stamp,
             sell_percent,
             stop_loss_percent,
             open_price):

    """ Takes in a stock, and a time and tests
        to see if the stock would sell because of
        a stop loss percent or sell because of a
        certain percent gain.                   """

    tz_east = pytz.timezone('US/Eastern')
    df_csv = pd.read_csv(file_name)


    # Gets stock data for the past 5 days in 5 minute intervals,
    # gets the last time of that data.
    # This is used to update the csv nextupdate column
    stock = yf.Ticker(stock_name)
    df = stock.history(period = "5d", interval = "5m")
    end_date_np = df.tail(1).index.values[0]
    end_date_pd = pd.to_datetime(end_date_np)
    end_date_tz = tz_east.localize(end_date_pd)
    new_update_timestamp = int(datetime.datetime.timestamp(end_date_tz))


    # Creates a sell price and a stop loss price,
    # based on the percentage entered into the function paramaters
    sell_price = open_price * (1 + (sell_percent / 100))
    stop_loss_price = open_price * (1 - (stop_loss_percent / 100))

    # Gets all stock data starting at the time of the timestamp
    df = df[datetime.datetime.fromtimestamp(time_stamp,tz_east):]


    # df of all high prices greater then sell variable
    df_sell = df["High"] >= sell_price
    # df of all low prices lower then stop loss variable
    df_stop = df["Low"] <= stop_loss_price


    # gets the index of the places where the price
    # was outside the parameters of the sell and stop prices
    sell_index = df_sell[df_sell == True].first_valid_index()
    try:
        sell_date = datetime.datetime.timestamp(sell_index)

    except:
        sell_date = None

    stop_index = df_stop[df_stop == True].first_valid_index()
    try:
        stop_date = datetime.datetime.timestamp(stop_index)
    except:
        stop_date = None



    # Returns the changed values of  csv depending on if the
    # stock hit the stop loss, sell stop, or nothing.
    if sell_date == None and stop_date == None:
        return["Next_Update",new_update_timestamp,"Sell_Price",None]


    elif sell_date != None and stop_date != None:

        if sell_date < stop_date:
            return("Next_Update","Gain","Sell_Price","Sold")

        elif stop_date < sell_date:
            return("Next_Update","Loss","Stop_Loss","Sold")


    elif sell_date == None:
        return("Next_Update","Loss","Stop_Loss","Sold")


    elif stop_date == None:
        return("Next_Update","Gain","Sell_Price","Sold")




def stock_open_price(stock_name, time_stamp):

    """ Takes in a stock name and timestamp
        returns the open price of the first
        available open price               """

    tz_east = pytz.timezone('US/Eastern')
    stock = yf.Ticker(stock_name)
    stock_data = stock.history(period = "5d", interval = "5m")
    valid_data = stock_data[datetime.datetime.fromtimestamp(time_stamp,tz_east):]
    try:
        open_price = valid_data.iloc[0]["Open"]
    except IndexError:
        return None

    return (open_price)



def find_testable_stocks(file_name, gain_percent, stop_percent):


    """ Filters through csv to find New
    stock that have not been tested. Filters
    them so that 24 hrs has past since they
    have been added to the read_csv         """



    # Filters csv for newly added stocks that
    # are a day old.

    df = pd.read_csv(file_name)
    filt = df["Next_Update"] == "New"
    df2 = df[filt]
    filt2 = df2["Time_Added"] < (time.time() - 86400)
    df2 = df2[filt2]

    # iterates through the new stocks,
    # updates the Open Price column of csv,
    # runs each stock through the backtest function,
    # updates csv
    for stock in df2.itertuples():
        index = stock[0]
        name = stock[1]
        time_stamp = stock[2]
        time_stamp = next_market_day(time_stamp)
        if time_stamp < (time.time()-86400):
            open_price = stock_open_price(name,time_stamp)
            df.loc[index,"Open_Price"] = open_price
            df.to_csv(file_name, index = False)
            if open_price != None:
                results  = backtest(file_name,
                                    index,
                                    name,
                                    time_stamp,
                                    gain_percent,
                                    stop_percent,
                                    open_price)
                if results != None:
                    df.loc[index, "Next_Update"] = results[1]
                    df.loc[index, results[2]] = results[3]
                    df.to_csv(file_name, index=False)
        else:
            pass



    # filters csv for stocks with a timestamp
    # in the Next Update column.
    # Confirms that at least a day has past
    # since the next availble open price.
    # Runs stocks through backtest function
    # and updates csv
    df = pd.read_csv(file_name)
    filt = df["Next_Update"] != "Loss"
    df2 = df[filt]
    filt = df2["Next_Update"] != "Gain"
    df2 = df2[filt]
    filt = df2["Next_Update"] != "New"
    df2 = df2[filt]

    series = df2.astype({"Next_Update": "float"})

    filt = series["Next_Update"] < (time.time() - 86400)
    df2 = df2[filt]
    for stock in df2.itertuples():
        index = stock[0]
        name = stock[1]
        time_stamp = stock[2]
        time_stamp = next_market_day(time_stamp)
        if time_stamp < (time.time()-86400):
            open_price = df.loc[index, "Open_Price"]
            results  = backtest(file_name,
                                index,
                                name,
                                time_stamp,
                                gain_percent,
                                stop_percent,
                                open_price)
            df.loc[index, "Next_Update"] = results[1]
            df.loc[index, results[2]] = results[3]
            df.to_csv(file_name, index=False)


update("WSB_Penny_5&4.csv")
update("WSB_Penny_6&4.csv")
update("WSB_Penny_7&4.csv")
update("WSB_Penny_8&4.csv")
update("WSB_Penny_9&4.csv")

find_testable_stocks("WSB_Penny_5&4.csv",5,4)
find_testable_stocks("WSB_Penny_6&4.csv",6,4)
find_testable_stocks("WSB_Penny_7&4.csv",7,4)
find_testable_stocks("WSB_Penny_8&4.csv",8,4)
find_testable_stocks("WSB_Penny_9&4.csv",9,4)

