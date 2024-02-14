import yfinance as yf
import pandas as pd
import requests
import design as d
from millify import millify
from config import secrets

def calculate_rsi(STOCK, ALPHA_KEY):
    try:
        url = f'https://www.alphavantage.co/query?function=RSI&symbol={STOCK}&interval=weekly&time_period=10&series_type=open&apikey={ALPHA_KEY}'
        r = requests.get(url)
        data = r.json()
        print(data)
        recent = data['Meta Data']['3: Last Refreshed']
        print(recent)
        rsi = float(data['Technical Analysis: RSI'][recent]['RSI'])
        return round(rsi, 2)
    except Exception as e:
        print(f"Error in calculate_rsi: {e}")
        return None


def rsi_statement(rsi):
    if type(rsi) == float:
        if rsi > 90:
            return 'Extremely overbought'
        elif rsi > 70:
            return 'Overbought'
        elif rsi < 10:
            return 'Extremely oversold'
        elif rsi < 30:
            return 'Oversold'
        elif 30 <= rsi <= 70:
            return 'Neutral zone, possible fair pricing'
        elif 50 < rsi <= 70:
            return 'Moderate bullish momentum'
        elif 30 <= rsi < 50:
            return 'Moderate bearish momentum'
        else:
            return 'Balance between buying + selling pressure'
    else:
        return '-'

def growth_recent_y(ticker):
    # returns a list of rev growth yoy
    # get recent year date: [0][0]
    # get recent year annual rev growth: [0][1] - returns float
    # get past year date: [1][0]
    # get past year annual rev growth: [1][1] - returns float
    stock_name = yf.Ticker(ticker)
    data = stock_name.income_stmt
    # print(stock_name.balance_sheet)

    total_revenue_row = data.loc['Total Revenue']
    # print(total_revenue_row)

    annual_rev_growth = []

    # Determine the number of years of data to process (up to 3)
    num_years = min(3, len(total_revenue_row) - 1)  # "-1" to make sure there's a previous year to compare to

    for i in range(num_years):
        try:
            total_rev = total_revenue_row.iloc[i]
            total_rev_prev_yr = total_revenue_row.iloc[i + 1]
            date = total_revenue_row.index[i].year

            if total_rev_prev_yr != 0: # avoid division by zero
                rev_growth = ((total_rev - total_rev_prev_yr)/ total_rev_prev_yr) * 100
            else:
                rev_growth = None

            annual_rev_growth.append([date, rev_growth])
        except IndexError:
            break
        except ZeroDivisionError: #  Handle the case where the denominator might be zero
            annual_rev_growth.append([date, '- '])

    return annual_rev_growth if annual_rev_growth else False


def difference_growth(year, prev_yr):
    # returns tuple, [0] is trending in str, [1] is T/F, needed for color_growth
    try:
        difference = year - prev_yr
        if difference > 0:
            difference = millify(difference, precision=2)
            return f'↑ {difference}% last Y', True
        else:
            difference = millify(difference, precision=2)
            return f'🔻 {difference}% last Y', False
    except:
        return '-', None

# diff = difference_growth(arg[0][1], arg[1][1])
# print()


def color_growth(difference):
    # returns color code for revenue growth number
    # need difference_growth()[1]
    if difference:
        return f'{d.green}'
    elif difference == False:
        return f'{d.red}'
    else:
        return f'{d.grey}'


if __name__ == "__main__":
    rsi = calculate_rsi('ENPH', secrets.ALPHA_API)
    print(rsi_statement(rsi))
    arg = growth_recent_y('CART')
    print(arg)