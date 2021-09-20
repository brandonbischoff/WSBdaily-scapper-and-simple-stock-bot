# WSBdaily-Scapper-and-Simple-Stock-Bot
A program that scapes WSB Daily website for stocks and tracks them.

Requirments: pandas
             yfinance
             requests
             bs4
             re
             
Instructions:
Before running this program, create a csv file with the columns = Name,
                                                                  Time_Added, 
                                                                  Source, 
                                                                  Next_Update, 
                                                                  Open_Price, 
                                                                  Sell_price, 
                                                                  Stop_loss
                                                                  
Enter your csv file name into the function at the bottom of the code.
Run the code daily.


Description:

This program scrapes WSBdaily's pennystock webpage and returns all the stocks
and there source that they came from ex. Reddits penny stocks daily plays.

It then keeps a csv file of these stocks and when they first appeared on the
webpage. The code then gets the chart data of each stock and gets the next available
open price and documents the price. The data is analyzed to see if the stock would sell
because it hit a stop loss price or because it hit a set sell price. The sell prices are 
based off a percentage entered into the backtest function.

I use crontab to run this program daily.





Topics learned:

Pandas module
regular expressions
working with datetime objects
webscrapping
crontab
