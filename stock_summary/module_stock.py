import requests
import design as d
import datetime
from config import secrets

# TODAY = datetime.datetime.today()
# print(TODAY)

# STOCK = "IBM"
# COMPANY_NAME = "Tesla Inc"

ALPHA_API = secrets.ALPHA_API

def request_income(STOCK, ALPHA_KEY):
    income = f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={STOCK}&apikey={ALPHA_KEY}'
    r = requests.get(income)
    income_statement = r.json()
    # print(income_statement)

    return income_statement


def request_stock(STOCK, ALPHA_KEY):
    stock = f'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol={STOCK}&apikey={ALPHA_KEY}'
    # stock = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={STOCK}&outputsize=full&apikey={ALPHA_KEY}'
    r = requests.get(stock)
    stock_price_data = r.json()
    # print(stock_price_data)

    return stock_price_data


def get_daily_price(stock_price_data):
    # returns today's closing rate as float, rounded to 2 decimal points, ie: 124.12

    last_refreshed = stock_price_data["Meta Data"]["3. Last Refreshed"]
    daily_price = float(stock_price_data['Monthly Time Series'][last_refreshed]['4. close'])
    daily_price = round(daily_price, 2)

    return daily_price

def get_lowest_last_month(stock_price_data):
    # returns the previous month's lowest rate as float, rounded to 2 decimal points, ie: 124.12

    last_month = list(stock_price_data['Monthly Time Series'])[1]
    lowest_last_month = float(stock_price_data['Monthly Time Series'][last_month]['3. low'])
    lowest_last_month = round(lowest_last_month, 2)

    return lowest_last_month


def get_lowest_ninety_day(stock_price_data):
    # returns the previous 3-month's lowest rate as float, rounded to 2 decimal points, ie: 124.12

    months = list(stock_price_data['Monthly Time Series'])
    three_months = []
    for i in months:
        if months.index(i) == 1 or months.index(i) == 2 or months.index(i) == 3:
            three_months.append(float(stock_price_data['Monthly Time Series'][i]['3. low']))
    if three_months:
        lowest_ninety_day = round(min(three_months), 2)
        return lowest_ninety_day
    else:
        return False

# print(request_stock('ENPH', ALPHA_API))


def get_lowest_in_year(stock_price_data):
    # returns the prev 365 days lowest rate as float, rounded to 2 decimal points, ie 124.12

    months = list(stock_price_data['Monthly Time Series'])
    last_year = []
    for i in range(1,13):
        for j in months:
            if months.index(j) > 13:
                break
            else:
                if months.index(j) == i:
                    last_year.append(float(stock_price_data['Monthly Time Series'][j]['3. low']))
    # print(last_year)
    if last_year:
        lowest_in_year = round(min(last_year), 2)
        return lowest_in_year
    else:
        return False


def get_difference_w_today(today, month, ninety, year):
    month_difference = today - month
    ninety_difference = today - ninety
    year_difference = today - year
    return round(month_difference, 1), round(ninety_difference, 1), round(year_difference, 1)

def month_descrip(difference):
    # returns trending description for the previous month's lowest price vs today's price
    if difference > 0:
        return f'TDY ↑ {difference}'
    else:
        return f'TDY 🔻{difference}'


# def month_color(month_difference):
#     # use with get_difference_w_today, specifically get index 0 - 'month'
#
#     if month_difference > 0:
#         return f'{d.red}'
#     else:
#         return f'{d.green}'

def ninety_descrip(difference):
    # returns trending description for the previous ninety day's lowest price vs today's price
    if difference > 0:
        return f'TDY ↑ {difference}'
    else:
        return f'TDY 🔻{difference}'


def year_descrip(difference):
    # returns trending description for the previous 365 day's lowest price vs today's price

    if difference > 0:
        return f'TDY ↑ {difference}'
    else:
        return f'TDY 🔻{difference}'


def buy_signal_price(month_difference):
    # return buy signal - if the difference between today's price and last month lowest is negative (ie stock dropped), then it will say should buy

    if month_difference > 9:
        return f'Buy signal: 👎'
    elif month_difference < 0:
        return f'Buy signal: 👍'
    else:
        return f'Buy signal: ?'



# DAILY_PRICE = get_daily_price(request_stock('IBM', 'demo'))
# print(DAILY_PRICE)
# LOW_LAST_MONTH = get_lowest_last_month(request_stock('IBM', 'demo'))
# print(LOW_LAST_MONTH)
# NINETY_DAY = get_lowest_ninety_day(request_stock('IBM', 'demo'))
# LOWEST_IN_YEAR = get_lowest_in_year(request_stock('IBM', 'demo'))
# difference = get_difference_w_today(DAILY_PRICE, LOW_LAST_MONTH, NINETY_DAY, LOWEST_IN_YEAR)
# print(difference)
# print(MONTH_DESCRIP(difference[0]))
# print(buy_signal_price(difference[0]))