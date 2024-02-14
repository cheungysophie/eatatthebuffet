import yfinance as yf
import csv
import pandas
try:
    import profit_margin
except:
    from . import profit_margin
from millify import millify
import design as d

pandas.set_option('display.max_columns', None)
pandas.set_option('display.max_rows', None)


def get_industry_name(ticker):
    # get industry name from s_data (get_stock_info)

    stock_name = yf.Ticker(ticker)
    in_name = stock_name.info['industry']
    # print(f'name on yahoo finance {in_name}')
    return in_name


def get_industry_npm(ticker):
    industry_name = get_industry_name(ticker).replace('—', ' _ ')
    # print(f'after replaced: {industry_name}')
    # USED IN NEWSLETTER
    # retrieve industry pe from industry_pe.py OR industry_pe.csv
    # if industry name not found, it will return '-'

    in_pm_info = profit_margin.pm_dict
    # in_pm_info = False

    try:
        try:
            if in_pm_info:
                in_pm = in_pm_info[industry_name]['npm']
                # print(in_pm)
                return round(in_pm, 2)
            else:
                with open("./stock_summary/profit_margin.csv") as f:
                    reader = csv.DictReader(f)
                    for i in reader:
                        if i['Industry'] == industry_name:
                            # print(i)
                            in_pm = float(i['Avg Net Profit Margin'])
                            return round(in_pm, 2)
        except:
            print('embedded expcept')
            if in_pm_info:
                industry_name.replace('-', '—')
                in_pm = in_pm_info[industry_name]['npm']
                print(in_pm)
                return round(in_pm, 2)
    except KeyError as traceback:
        print(traceback)
        print('Error finding industry name, may need manual searching')
        return False


def get_stock_npm_yearly(ticker):
    # gets most recent year as date: prev_npm[0][0]. get most recent npm prev_npm[0][1]
    # returns a list ie: [[2022, -66.73738445218973], [2021, 11.547204121836643], [2020, 9.9409001363843], [2019, 15.18411880587968]]
    # returns the prev 4 calendar year net profit margin as a list
    # net profit margin = net income (income after ALL expenses) / total revenue
    stock_name = yf.Ticker(ticker)
    data = stock_name.income_stmt
    # print(data)

    prev_npm = []

    # Get 'Net Income' and 'Total Revenue' rows from the DataFrame
    net_income_row = data.loc['Net Income']
    total_revenue_row = data.loc['Total Revenue']

    # Determine how many years of data to process (up to 4)
    num_years = min(4, len(net_income_row))

    for i in range(num_years):
        try:
            net_income = net_income_row.iloc[i]
            total_revenue = total_revenue_row.iloc[i]
            date = net_income_row.index[i].year


            net_profit_margin = net_income / total_revenue * 100
            # print(net_profit_margin)
            prev_npm.append([date, net_profit_margin])
        except IndexError:
            # This should not be reached due to the min(4, len(net_income_row)) check, but is kept just in case
            break
        except ZeroDivisionError:
            # Handle the case where total_revenue might be zero, and net profit margin can't be computed.
            prev_npm.append([date, '- '])
    return prev_npm if prev_npm else False



def get_stock_npm_quarterly(ticker):
    # gets most recent year as date: prev_gpm[0][0]. get most recent gpm prev_gpm[0][1]
    # returns a list ie: [[2022, -66.73738445218973], [2021, 11.547204121836643], [2020, 9.9409001363843], [2019, 15.18411880587968]]
    # returns the prev 4 calendar year gross profit margin as a list
    # gross profit margin = gross profit (COGS) / total revenue
    stock_name = yf.Ticker(ticker)
    data = stock_name.quarterly_incomestmt

    prev_npm_quarterly = []
    for i in range(0, 4):
        try:
            for (index, row) in data.iterrows():
                if index == 'Net Income':
                    net_income = row.iloc[i]
                    date = row.index[i].date()
                if index == 'Total Revenue':
                    total_revenue = row.iloc[i]

            net_profit_margin = net_income / total_revenue * 100
            prev_npm_quarterly.append([date, net_profit_margin, net_income, total_revenue])
        except IndexError:
            break
        except ZeroDivisionError:
            prev_npm_quarterly.append([date, '- ', net_income, total_revenue])

    return prev_npm_quarterly


def get_quarter_difference(quarterly_dict, ticker):
    try:
        recent_quart = quarterly_dict[0][1]
        quart_bf_l = quarterly_dict[1][1]

        difference = round(recent_quart - quart_bf_l, 1)

        if difference > 0:
            return f'↑ {difference}% QoQ', True, f'{d.green}'
        else:
            return f'🔻 {difference}% QoQ', False, f'{d.red}'
    except (IndexError, TypeError):
        return f'<a style="color: #000" href="https://finance.yahoo.com/quote/{ticker}">View More</a>', False, f'{d.grey}'


def npm_statement(quarter, ticker, difference):
    # for quarter - need get_stock_gpm_quarterly()
    # difference - get_quarter_difference() [1]
    try:
        industry_npm = get_industry_npm(ticker)
    except:
        industry_npm = False
    recent_total_revenue = millify(quarter[0][3], precision=2)
    recent_net_income = millify(quarter[0][2], precision=2)
    if industry_npm:
        if difference:
            if quarter[0][1] > industry_npm:
                return f"Total revenue: ${recent_total_revenue}, net income: ${recent_net_income}, {ticker}'s NPM increased from the last Q. Compared to the industry annual avg of {industry_npm}%, this is a good sign."
            else:
                return f"Total revenue: ${recent_total_revenue}, net income: ${recent_net_income}, {ticker}'s NPM increased from the last Q. Compared to the industry annual avg of {industry_npm}%, this is not a good sign."
        else:
            if quarter[0][1] > industry_npm:
                return f"Total revenue: ${recent_total_revenue}, net income: ${recent_net_income}, {ticker}'s NPM decreased from the last Q. Compared to the industry annual avg of {industry_npm}%, this is a good sign."
            else:
                return f"Total revenue: ${recent_total_revenue}, net income: ${recent_net_income}, {ticker}'s NPM decreased from the last Q. Compared to the industry annual avg of {industry_npm}%, this is not a good sign."
    else:
        if difference:
            return f"Total revenue recent Q: ${recent_total_revenue}. Gross profit recent Q: ${recent_net_income}."
    return ' '

# annual = get_stock_npm_yearly('META')
# quarter = get_stock_npm_quarterly("META")
# print(f'quarter {quarter}')
# print(get_quarter_difference(quarter))
# print(NPM_STATEMENT(quarter, 'META', get_quarter_difference(quarter)))


def get_prev_year_difference(annual_dict):
    try:
        recent_year = annual_dict[0][1]
        year_bf_l = annual_dict[1][1]

        difference = round(recent_year - year_bf_l, 1)

        if difference > 0:
            return f'↑ {difference}% YoY', True, f'{d.green}'
        else:
            return f'🔻 {difference}% YoY', False, f'{d.red}'
    except (IndexError, TypeError):
        return '-', False, f'{d.grey}'


def get_year_bf_l_difference(annual_dict):
    try:
        year_bf_l = annual_dict[1][1]
        year_bf_that = annual_dict[2][1]

        difference = round(year_bf_l - year_bf_that, 1)

        if difference > 0:
            return f'↑ {difference}% YoY', True, f'{d.green}'
        else:
            return f'🔻 {difference}% YoY', False, f'{d.red}'
    except (IndexError, TypeError):
        return '-', False, f'{d.grey}'


# print(get_prev_year_difference(annual))
# print(get_year_bf_l_difference(annual))

def buy_signal(year_difference, quarter_difference):
    # for year difference, need to add [1]
    # for quarter difference, need to add [1]
    if year_difference and quarter_difference:
        return f'Buy signal: 👍'
    elif year_difference or quarter_difference:
        return f'Buy signal: ?'
    else:
        return f'Buy signal: 👎'

# print(BUY_SIGNAL_STOCK(get_prev_year_difference(annual)[1], get_quarter_difference(quarter)[1]))

# print(get_industry_gpm('IBM'))

if __name__ == "__main__":
    ticker = 'SGML'
    print(get_stock_npm_yearly('SGML'))
    print(get_prev_year_difference(get_stock_npm_yearly('SGML')))
    print(get_year_bf_l_difference(get_stock_npm_yearly('SGML'), ticker))
    print(get_stock_npm_yearly('AAPL'))
    print(get_stock_npm_quarterly('SGML'))