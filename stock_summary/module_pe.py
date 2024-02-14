import yfinance as yf
try:
    import industry_pe
except:
    from . import industry_pe
import csv


def get_stock_pe(ticker):
    # USED IN NEWSLETTER
    stock_name = yf.Ticker(ticker)
    print(stock_name.info)
    try:
        pe = stock_name.info['trailingPE']
        return round(pe, 2)
    except:
        return '-'


def get_industry_name(ticker):
    # get industry name from s_data (get_stock_info)

    stock_name = yf.Ticker(ticker)
    in_name = stock_name.info['industry']
    return in_name


def get_industry_pe(ticker):
    industry_name = get_industry_name(ticker)
    # USED IN NEWSLETTER
    # retrieve industry pe from industry_pe.py OR industry_pe.csv
    # if industry name not found, it will return '-'

    in_pe_info = industry_pe.pe_dict
    in_pe_info = False

    try:
        if in_pe_info:
            in_pe = float(in_pe_info[industry_name])
            return round(in_pe, 2)
        else:
            with open("./stock_summary/industry_pe.csv") as f:
                reader = csv.DictReader(f)
                for i in reader:
                    if i['Industry'] == industry_name:
                        # print(i)
                        in_pe = float(i['PE Ratio'])
                        return round(in_pe, 2)
    except KeyError as error_message:
        print('Error finding industry name, may need manual searching')
        return False


#TODO redefine PE_STATEMENT after tam
def pe_statement(ind_pe, stock_pe, ticker):
    if stock_pe != '-':
        if stock_pe <= ind_pe:
            return f'P/E is lower than industry avg, if slow rev growth and small TAM, there could be a lack of growth prospects. Otherwise, {ticker} could be undervalued.'
            # pe could be undervalued if lower than ind_pe
            # low pe could be due to lack of growth prospects - should check revenue growth & TAM
        else:
            return f'P/E is higher than industry avg, if {ticker} is a growth stock, there could be high returns but also high risk. Could also be overvalued.'
            # company could be growth stock (potential high return) == high risk
    else:
        return f'{ticker} has no trailing P/E data, possibly because it is not profitable'

# print(get_stock_info('IBM').info)
# print(get_stock_pe('IBM'))
# print(get_industry_name('TSLA'))