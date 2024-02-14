import yfinance as yf
import pandas

pandas.set_option('display.max_columns', None)
pandas.set_option('display.max_rows', None)


def get_company_name(ticker):
    stock_name = yf.Ticker(ticker)
    info = stock_name.info
    n = info['shortName'].strip()
    print(n)
    if ',' in n:
        name = n.split(',')[0].strip()
    elif '(' in n:
        name = n.split('(')[0].strip()
    elif 'Inc' in n:
        name = n.split('Inc')[0].strip()
    elif 'Corporation' in n:
        name = n.split('Corporation')[0].strip()
    return name


def get_company_descrip(ticker):
    stock_name = yf.Ticker(ticker)
    info = stock_name.info
    return info['longBusinessSummary']


if __name__ == "__main__":
    ticker = 'AMD'
    print(get_company_name(ticker))
    print(get_company_descrip(ticker))