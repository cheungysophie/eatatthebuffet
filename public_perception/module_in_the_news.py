import requests, json, os, datetime
import openai
import nltk
import pandas as pd
import stocksent.get_sentiment_data
import traceback
from urllib.parse import quote
from config import secrets



from nltk.sentiment import SentimentIntensityAnalyzer
vader = SentimentIntensityAnalyzer(lexicon_file="/Users/sophie/PycharmProjects/eat_at_the_buffet/venv/lib/python3.11/site-packages/nltk/sentiment/vader_lexicon.txt")
from stock_summary import module_stock_info as stock
from stocksent import Sentiment
import pandas

pandas.set_option('display.max_columns', None)
pandas.set_option('display.max_rows', None)

newsKey = secrets.newsKey
category = 'general'
pageSize = 100
today_date = datetime.date.today()
difference = datetime.timedelta(days=7)
startDate = today_date - difference

def get_company_news(ticker):
    # returns a dictionary of news from the past 7 days
    # company_dict[0]['short_title'] - returns first 33 characters
    # company_dict[0]['title'] - returns full title name
    # company_dict[0]['url'] - returns url link
    # company_dict[0]['source'] - returns source link

    company_dict = {}
    number = 0

    try:
        company_name = stock.get_company_name(ticker).strip()
        print(company_name)
        encoded_name = quote(company_name)
        print(encoded_name)
        url = f'https://newsapi.org/v2/everything?q={encoded_name}&language=en&from={startDate}&pageSize={pageSize}&sortBy=popularity&apiKey={newsKey}'
        print(url)
        result = requests.get(url)
        data = result.json()

        for article in data['articles']:
            company_name = company_name.replace('+', ' ')
            company_name = company_name.replace('%26', '&')
            print(company_name)
            if company_name in article['title']:
                if 'https://arstechnica.com/shopping/' in article['url']:
                    continue
                else:
                    title = article['title']
                    if len(title) > 33:
                        short_title = title[:26] + '...'
                    else:
                        short_title = title
                    company_dict[number] = {
                        'short_title': short_title,
                        'title': article['title'],
                        'url': article['url'],
                        'source': article['source']['name']
                    }
                    number+=1
        return company_dict
    except Exception as e:
        print(e)
        return None


def get_sentiment(ticker):
    # gets sentiment from the past 7 days
    try:
        stock = Sentiment(ticker)
        sentiment_score = stock.get_sentiment() # returns float
        print(sentiment_score)
    except Exception:
        traceback.print_exc()
        return '-'

    if -1 <= sentiment_score < -0.8:
        return '🤬', 'Most Negative'
    elif -0.8 <= sentiment_score < -0.6:
        return '😨', 'Strongly Negative'
    elif -0.6 <= sentiment_score < -0.4:
        return '😥', 'Moderately Negative'
    elif -0.4 <= sentiment_score < -0.2:
        return '😟', 'Slightly Negative'
    elif -0.2 <= sentiment_score < 0:
        return '🙁', 'Neutral Negative'
    elif 0 <= sentiment_score < 0.2:
        return '🙂', 'Neutral Positive'
    elif 0.2 <= sentiment_score < 0.4:
        return '😊', 'Slightly Positive'
    elif 0.4 <= sentiment_score < 0.6:
        return '😃', 'Moderately Positive'
    elif 0.6 <= sentiment_score < 0.8:
        return '😁', 'Strongly Positive'
    elif 0.8 <= sentiment_score <= 1:
        return '🥳', 'Most Positive'


def get_gpt_summary(ticker, dict, sentiment):
    if dict:
        article_list = list(dict.values())
        short = []
        for i in article_list:
            short.append((i['title'], i['source']))

        openai.api_key = secrets.OPEN_API
        openai.organization = secrets.OPEN_ORG
        openai.Model.list()
        print(short)
        prompt = f"Analyze {ticker}'s outlook based on {short}, and {sentiment}. Summarize the outline in 30 words. Don't mention advice or analyst outlooks. Do not mention the sentiment that I provided you again."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
              temperature=1,
              max_tokens=256,
              top_p=1,
              frequency_penalty=0,
              presence_penalty=0
        )
        print(response)

        return response['choices'][0]['message']['content']
    else:
        return ' '



if __name__ == "__main__":
    ticker = 'T'
    dict = get_company_news(ticker)
    print(dict)

    sentiment = get_sentiment(ticker)
    print(get_gpt_summary(ticker, dict, sentiment))