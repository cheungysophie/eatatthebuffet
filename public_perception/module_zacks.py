import requests
import urllib3.contrib.pyopenssl
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import design as d
import html

# Cannot just use requests: The error message WRONG_SIGNATURE_TYPE suggests that there's a mismatch in the SSL/TLS configuration between your client and the server you're trying to communicate with. Specifically, the server might be using a signature algorithm that's not supported by the SSL/TLS library on your client.
# Inject pyOpenSSL into urllib3
urllib3.contrib.pyopenssl.inject_into_urllib3()

def get_zacks_rank(ticker):
    # returns zacks ranking as list
    # zacks_rank[0] returns ranking in number form (str), '3'
    #zacks_rank[1] returns ranking in text form (str), 'hold'
    url = f'https://quote-feed.zacks.com/index?t={ticker}'

    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx and 5xx)
    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}')
        return False  # or you might want to re-raise the exception or handle it in another way

    data_str = response.json()
    zacks_rank = []
    # print(data_str)
    zacks_rank.append(data_str[ticker]["zacks_rank"])
    zacks_rank.append(data_str[ticker]["zacks_rank_text"])
    return zacks_rank

def get_zacks_statement(ranking, ticker):
    # need [0] of ranking
    if ranking == '1':
        return f'<a style="color: #000" target="_blank" href=https://www.zacks.com/stock/quote/{ticker}>Projection</a>: greatly outperform the S&P 500 in the next 1-3mo. Avg ~24.17% annualized return'
    elif ranking == '2':
        return f'<a style="color: #000" target="_blank" href=https://www.zacks.com/stock/quote/{ticker}>Projection</a>: outperform the S&P 500 in the next 1-3mo. Avg ~17.86% annualized return'
    elif ranking == '3':
        return f'<a style="color: #000" target="_blank" href=https://www.zacks.com/stock/quote/{ticker}>Projection</a>: perform in line with the S&P 500 in the next 1-3mo. Avg of ~9.20% annualized return'
    elif ranking == '4':
        return f'<a style="color: #000" target="_blank" href=https://www.zacks.com/stock/quote/{ticker}>Projection</a>: under-perform the S&P 500 in the next 1-3mo. Avg of ~5.01% annualized return'
    elif ranking == '5':
        return f'<a style="color: #000" target="_blank" href=https://www.zacks.com/stock/quote/{ticker}>Projection</a>: greatly under-perform the S&P 500 in the next 1-3mo. Avg of ~2.50% annualized return'
    else:
        return False



def get_zacks_score(ticker):
    # when using it in newsletter: CHECK IF THIS IS TRUE FIRST
    # returns a dict like: {'Value': {'Score': 'D', 'Text': 'A Bit Pricey', 'Color': '#FA5D5D'}, 'Growth': {'Score': 'A', 'Text': 'Rapid Growth', 'Color': '#44931F'}}
    # get zacks value score: dict['Value']['Score']
        # get text version of score: dict['Value']['Text']
        # get color of value score: dict['Value]['Color']
    # get zacks growth score: dict['Growth']['Score']

    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # This is the correct way to set the headless option for Chrome

        url = f'https://www.zacks.com/stock/research/{ticker}/stock-style-scores/'

        # Ensure you have the chromedriver in your PATH or specify the path explicitly
        browser = webdriver.Chrome(options=chrome_options)
        browser.get(url)
        html_source = browser.page_source
        soup = BeautifulSoup(html_source, "lxml")
        browser.quit()  # It's a good practice to use quit instead of close when you want to end the session

        table = soup.find_all("p", {'class': 'rank_view'})
        if not table:
            return False

        ranking = table[1].text.split('|')
        cleaned_values = [value.strip().replace('\xa0', ' ').split(' ') for value in ranking]
        print(cleaned_values)

        styles_dict = {}
        for row in cleaned_values:
            for item in row:
                if item == 'Value':
                    styles_dict['Value'] = {}
                    styles_dict['Value']['Score'] = row[0]
                    if row[0] == 'A':
                        styles_dict['Value']['Text'] = 'Top Value'
                        styles_dict['Value']['Color'] = d.green
                    elif row[0] == 'B':
                        styles_dict['Value']['Text'] = 'Above-Avg'
                        styles_dict['Value']['Color'] = d.dark_green
                    elif row[0] == 'C':
                        styles_dict['Value']['Text'] = 'Reasonable'
                        styles_dict['Value']['Color'] = d.orange
                    elif row[0] == 'D':
                        styles_dict['Value']['Text'] = 'A Bit Pricey'
                        styles_dict['Value']['Color'] = d.red
                    elif row[0] == 'F':
                        styles_dict['Value']['Text'] = 'Too Expensive'
                        styles_dict['Value']['Color'] = d.dark_red
                if item == 'Growth':
                    styles_dict['Growth'] = {}
                    styles_dict['Growth']['Score'] = row[0]
                    if row[0] == 'A':
                        styles_dict['Growth']['Text'] = 'Rapid Growth'
                        styles_dict['Growth']['Color'] = '#44931F'
                    elif row[0] == 'B':
                        styles_dict['Growth']['Text'] = 'Solid Grower'
                        styles_dict['Growth']['Color'] = '#31631A'
                    elif row[0] == 'C':
                        styles_dict['Growth']['Text'] = 'Stable Future'
                        styles_dict['Growth']['Color'] = '#FA9F5D'
                    elif row[0] == 'D':
                        styles_dict['Growth']['Text'] = 'Future TBD...'
                        styles_dict['Growth']['Color'] = '#FA5D5D'
                    elif row[0] == 'F':
                        styles_dict['Growth']['Text'] = 'Dead End'
                        styles_dict['Growth']['Color'] = '#DE0E0E'
                # else:
                #     print(f"Styles dict created but error creating new clean dict")
                #     return False
        if not styles_dict:
            print(f"No styles dict created")
            return False
        return styles_dict

    except Exception as e:
        print(f"An error occurred with getting zacks style score dict: {e}")
        return False

if __name__ == "__main__":
    # Call the function with the ticker 'AAPL'
    ticker = 'AAPL'
    print(get_zacks_rank(ticker)[0])
    print(get_zacks_rank(ticker)[1])
    print(get_zacks_statement(get_zacks_rank(ticker)[0], ticker))
    print(get_zacks_score(ticker))