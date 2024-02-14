import yfinance as yf
from millify import millify
import csv
import pandas
import design as d


pandas.set_option('display.max_columns', None)
pandas.set_option('display.max_rows', None)


def get_industry_name(ticker):
    # get industry name from s_data (get_stock_info)

    stock_name = yf.Ticker(ticker)
    in_name = stock_name.info['industry']
    # print(f'name on yahoo finance {in_name}')
    return in_name


def get_industry_roe(ticker):
    industry_name = get_industry_name(ticker).replace('—', ' _ ')
    print(f'after replaced: {industry_name}')
    # USED IN NEWSLETTER
    # retrieve industry roe from industry_roe.csv
    # if industry name not found, it will return False

    try:
        try:
            with open("./stock_summary/industry_roe.csv") as f:
                reader = csv.DictReader(f)
                for i in reader:
                    if i['Industry'] == industry_name:
                                # print(i)
                        in_pm = float(i['ROE (unadjusted)'])
                        return round(in_pm, 2)
        except:
            with open("./industry_roe.csv") as f:
                reader = csv.DictReader(f)
                for i in reader:
                    if i['Industry'] == industry_name:
                                # print(i)
                        in_pm = float(i['ROE (unadjusted)'])
                        return round(in_pm, 2)

    except KeyError as traceback:
        print(traceback)
        print('Error finding industry name, may need manual searching')
        return False

# print(get_industry_roe('IBM'))

def calendar_3_yr_roe(ticker):
    # get most recent year as date: prev_roe[0][0], get most recent roe prev_roe[0][1]
    # returns a list ie: [[2022, 7.47], [2021, 26.17], [2020, 25.47], [2019, 42.98]]
    # return the previous 3 calendar year return on equity as a list
    stock_name = yf.Ticker(ticker)

    prev_roe = []
    try:
        try:
            for i in range(0, 3):
                data = stock_name.balance_sheet
                for (index, row) in data.iterrows():
                    if index == 'Common Stock Equity':
                        common_stock_equity = row.iloc[i]
                        common_stock_equity_prev_yr = row.iloc[i + 1]
                    date = row.index[i].year

                data = stock_name.income_stmt
                # get net income from annual report
                for (index, row) in data.iterrows():
                    if index == 'Net Income':
                        net_income_prev_yr = row.iloc[i]
                        # print(net_income_prev_yr)

                prev_yr_roe = (net_income_prev_yr / ((common_stock_equity_prev_yr + common_stock_equity) / 2)) * 100
                prev_roe.append([date, prev_yr_roe])
            return prev_roe
        except IndexError:
            for i in range(0, 2):
                data = stock_name.balance_sheet
                for (index, row) in data.iterrows():
                    if index == 'Common Stock Equity':
                        common_stock_equity = row.iloc[i]
                        common_stock_equity_prev_yr = row.iloc[i + 1]
                    date = row.index[i].year

                data = stock_name.income_stmt
                # get net income from annual report
                for (index, row) in data.iterrows():
                    if index == 'Net Income':
                        net_income_prev_yr = row.iloc[i]
                        # print(net_income_prev_yr)

                prev_yr_roe = (net_income_prev_yr / ((common_stock_equity_prev_yr + common_stock_equity) / 2)) * 100
                prev_roe.append([date, prev_yr_roe])
            return prev_roe

    except:
        return False

# c_4_yr = calendar_3_yr_roe('ILMN')
# print(c_4_yr)

def stock_net_income_prev_year(ticker):
    # return the previous 4 calendar year return on equity as a list, ie: [[2022, 7.47], [2021, 26.17], [2020, 25.47], [2019, 42.98]]
    stock_name = yf.Ticker(ticker)

    data = stock_name.balance_sheet
    for (index, row) in data.iterrows():
        if index == 'Common Stock Equity':
            common_stock_equity = row.iloc[0]
            common_stock_equity_prev_yr = row.iloc[1]
            common_stock_equity_prev_yr = millify((common_stock_equity_prev_yr + common_stock_equity) / 2, precision=2)


        # get net income from annual report
    data = stock_name.income_stmt
    for (index, row) in data.iterrows():
        if index == 'Net Income':
            net_income_prev_yr = row.iloc[0]
            if net_income_prev_yr > 0:
                profit = True
            else:
                profit = False
            net_income_prev_yr = millify(net_income_prev_yr, precision=2)

    return common_stock_equity_prev_yr, net_income_prev_yr, profit


def roe_color_this_year(year, prev_year):
    if year > prev_year:
        return f'{d.green}'
    else:
        return f'{d.red}'


def roe_statement(common_stock, profit, net_income, prev_yr_roe, ticker, industry_roe):
    # returns roe statement
    # common stock = def stock_net_income_prev_year [0]
    # profit = def stock_net_income_prev_year [2]
    # net income = def stock_net_income_prev_year [1]
    # prev_yr_roe = calendar_3_yr_roe[0][1]
    prev_yr_roe = millify(prev_yr_roe, precision=2)
    if industry_roe:
        if profit:
            return f'In the last year, {ticker} turned ${common_stock} investments (avg stock equity) into ${net_income} profit. Estimated industry annual avg is {industry_roe}%.'
        else:
            return f'In the last year, {ticker} turned ${common_stock} investments (avg stock equity) into ${net_income} loss. Estimated industry annual avg is {industry_roe}%.'
    else:
        if profit:
            return f'In the last year, {ticker} turned ${common_stock} investments (avg stock equity) into ${net_income} profit, a {prev_yr_roe}% return on equity.'
        else:
            return f'In the last year, {ticker} turned ${common_stock} investments (avg stock equity) into ${net_income} loss, a {prev_yr_roe}% return on equity.'


# print(stock_net_income_prev_year('ILMN'))
# print(ROE_STATEMENT(stock_net_income_prev_year('ILMN')[0], stock_net_income_prev_year('ILMN')[2], stock_net_income_prev_year('ILMN')[1], c_4_yr[0][1], 'ILMN'))


def ttm_roe(ticker):
    # shows the trailing-twelve-month return on equity (net income / total equity shares), returns float
    # from yahoo finance
    # shows how good the invested money is
    stock_name = yf.Ticker(ticker)
    data = stock_name.info
    ttm_roe = data['returnOnEquity']
    ttm_roe *= 100
    return round(ttm_roe, 2)


# print(ttm_roe('IBM'))