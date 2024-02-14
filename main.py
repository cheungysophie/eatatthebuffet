import time
import datetime as dt
from millify import millify
from config import send_email
from stock_summary import module_stock as stock, module_pe as pe, module_gross_profit_margin as gpm, module_net_profit_margin as npm, module_return_on_equity as roe, module_RSI_Growth as rsi
from public_perception import module_zacks as zachs, module_in_the_news as news
from config import secrets

ALPHA_API = secrets.ALPHA_API

# send report
send_report_admin_only = True
if send_report_admin_only:
    # if send report is True (on), it will only send to me
    tickers = ['ENPH'] # add the stock you want to check
    users = [{'email': secrets.admin_email, 'watchlist': {}}]
else:
    # if send report is False (off), it will send to any users who have that stock on their watchlist
    # any stocks on the watchlist should also be added here
    # this ensures that each stock is only checked ONCE, rather than requesting each stock again for each user
    from users import tickers, users


# EMAIL SENDING LOGIC ----------------------------------
for i in tickers:

    #region FETCH & PROCESS DATA --------------------------------
    stock_data = stock.request_stock(i, ALPHA_API)
    DAILY_PRICE = stock.get_daily_price(stock_data) # return float
    TICKER = i

    # STOCK MODULE ====================================
    # used in newsletter:
    LOW_LAST_MONTH = stock.get_lowest_last_month(stock_data) # 400.94
    NINETY_DAY = stock.get_lowest_ninety_day(stock_data) # 399.93
    LOWEST_IN_YEAR = stock.get_lowest_in_year(stock_data) # 410.32

    difference = stock.get_difference_w_today(DAILY_PRICE, LOW_LAST_MONTH, NINETY_DAY, LOWEST_IN_YEAR)
    difference_month = difference[0]
    difference_ninety = difference[1]
    difference_year = difference[2]

    MONTH_DESCRIP = stock.month_descrip(difference_month) # returns trending for month
    NINETY_DESCRIP = stock.ninety_descrip((difference_ninety)) # returns trending for ninety day
    YEAR_DESCRIP = stock.ninety_descrip(difference_year)
    BUY_SIGNAL_STOCK = stock.buy_signal_price(difference_month) # buy signal

    # PE MODULE
    STOCK_PE = pe.get_stock_pe(i)
    INDUS_PE = pe.get_industry_pe(i) #not typo here
    PE_STATEMENT = pe.pe_statement(INDUS_PE, STOCK_PE, i)

    # GROSS PROFIT MARGIN ==============================
    quarter_gpm_data = gpm.get_stock_gpm_quarterly(i)
    year_gpm_data = gpm.get_stock_gpm_yearly(i)
    quarter_diff_gpm = gpm.get_quarter_difference(quarter_gpm_data, i) # returns tuple
    year_diff_gpm = gpm.get_prev_year_difference(year_gpm_data) # returns tuple

    try:
        RECENT_Q_GPM = millify(quarter_gpm_data[0][1], precision=2) # 23.34
        RECENT_YEAR_GPM = millify(year_gpm_data[0][1], precision=2)
        YEAR_BF_L_GPM_NUMBER = millify(year_gpm_data[1][1], precision=2)
    except (TypeError, ValueError):
        RECENT_Q_GPM = quarter_gpm_data[0][1]
        RECENT_YEAR_GPM = year_gpm_data[0][1]
        YEAR_BF_L_GPM_NUMBER = year_gpm_data[1][1]

    RECENT_Q_COLOR_GPM = quarter_diff_gpm[2] # color code
    RECENT_Q_DIFF_GPM = quarter_diff_gpm[0]
    RECENT_YEAR_DATE_GPM = year_gpm_data[0][0]
    RECENT_YEAR_COLOR_GPM = year_diff_gpm[2]
    RECENT_YEAR_DIFF_GPM = year_diff_gpm[0]
    YEAR_BF_L_DATE_GPM = year_gpm_data[1][0]
    YEAR_BF_L_COLOR_GPM = gpm.get_year_bf_l_difference(year_gpm_data)[2]
    YEAR_BF_L_DIFF_GPM = gpm.get_year_bf_l_difference(year_gpm_data)[0]
    GPM_STATEMENT = gpm.gpm_statement(quarter_gpm_data, i, quarter_diff_gpm[1])
    BUY_SIGNAL_GPM = gpm.buy_signal(year_diff_gpm[1], quarter_diff_gpm[1])

    # NET PROFIT MARGIN =================================
    quarter_npm_data = npm.get_stock_npm_quarterly(i)
    year_npm_data = npm.get_stock_npm_yearly(i)
    quarter_diff_npm = npm.get_quarter_difference(quarter_npm_data, i)
    year_diff_npm = npm.get_prev_year_difference(year_npm_data)

    try:
        RECENT_Q_NPM = millify(quarter_npm_data[0][1], precision=2) # 23.34
        RECENT_YEAR_NPM_NUMBER = millify(year_npm_data[0][1], precision=2)
        YEAR_BF_L_NPM_NUMBER = millify(year_npm_data[1][1], precision=2)
    except (TypeError, ValueError):
        RECENT_Q_NPM = quarter_npm_data[0][1]
        RECENT_YEAR_NPM_NUMBER = year_npm_data[0][1]
        YEAR_BF_L_NPM_NUMBER = year_npm_data[1][1]


    RECENT_Q_COLOR_NPM = quarter_diff_npm[2]
    RECENT_Q_DIFF_NPM = quarter_diff_npm[0]
    RECENT_YEAR_DATE_NPM = year_npm_data[0][0]
    RECENT_YEAR_COLOR_NPM = year_diff_npm[2]
    RECENT_YEAR_DIFF_NPM = year_diff_npm[0]
    YEAR_BF_L_DATE_NPM = year_npm_data[1][0]
    YEAR_BF_L_COLOR_NPM = npm.get_year_bf_l_difference(year_npm_data)[2]
    YEAR_BF_L_DIFF_NPM = npm.get_year_bf_l_difference(year_npm_data)[0]
    NPM_STATEMENT = npm.npm_statement(quarter_npm_data, i, quarter_diff_npm[1])
    BUY_SIGNAL_NPM = npm.buy_signal(year_diff_npm[1], quarter_diff_npm[1])


    # RETURN ON EQUITY ===================================
    roe_3_yr_data = roe.calendar_3_yr_roe(i)

    try:
        RECENT_YEAR_ROE = millify(roe_3_yr_data[0][1], precision=2)  # ex: 23.23
        PREV_YEAR_ROE = millify(roe_3_yr_data[1][1], precision=2) # ex: 43.23
        YEAR_BF_L_ROE = millify(roe_3_yr_data[2][1], precision=2) # ex: 54.24
    except (TypeError, ValueError):
        RECENT_YEAR_ROE = roe_3_yr_data[0][1]  # ex: 23.23
        PREV_YEAR_ROE = roe_3_yr_data[1][1] # ex: 43.23
        YEAR_BF_L_ROE = roe_3_yr_data[2][1] # ex: 54.24


    RECENT_YEAR_DATE_ROE = roe_3_yr_data[0][0] # ex: 2022
    RECENT_YEAR_COLOR_ROE = roe.roe_color_this_year(roe_3_yr_data[0][1], roe_3_yr_data[1][1]) # returns color code
    PREV_YEAR_DATE_ROE = roe_3_yr_data[1][0] # ex: 2021
    YEAR_BF_L_DATE_ROE = roe_3_yr_data[2][0] # ex: 2020
    #roe statement
    common_stock_equity_recent_yr = roe.stock_net_income_prev_year(i)[0]
    net_income_recent_yr = roe.stock_net_income_prev_year(i)[1]
    profit_recent_yr = roe.stock_net_income_prev_year(i)[2]
    industry_roe = roe.get_industry_roe(i)

    ROE_STATEMENT = roe.roe_statement(common_stock_equity_recent_yr, profit_recent_yr, net_income_recent_yr, roe_3_yr_data[0][1], i, industry_roe)


    # RSI & GROWTH ======================================
    RSI_NUM = rsi.calculate_rsi(i, ALPHA_API) # returns RSI number
    RSI_TRENDING = rsi.rsi_statement(RSI_NUM)

    # past_year_date_arg = rsi.growth_recent_y(i)[1][0]
    recent_year_arg = rsi.growth_recent_y(i)[0][1]
    past_year_arg = rsi.growth_recent_y(i)[1][1]
    post_or_neg = rsi.difference_growth(recent_year_arg, past_year_arg)[1]

    RECENT_YEAR_DATE_ARG = rsi.growth_recent_y(i)[0][0]
    try:
        RECENT_YEAR_ARG_NUMBER = millify(recent_year_arg, precision=2)
    except:
        RECENT_YEAR_ARG_NUMBER = recent_year_arg
    ARG_TRENDING = rsi.difference_growth(recent_year_arg, past_year_arg)[0]
    COLOR_ARG = rsi.color_growth(post_or_neg)


    # ZACKS ============================================
    zacks_score = zachs.get_zacks_score(i)
    zacks_rank = zachs.get_zacks_rank(i)

    ZACKS_RANKING = zacks_rank[0]
    ZACKS_RANK_DESCRIP = zacks_rank[1]
    ZACKS_STATEMENT = zachs.get_zacks_statement(ZACKS_RANKING[0], i)
    ZACKS_VALUE_SCORE = zacks_score['Value']['Score']
    ZACKS_VALUE_TEXT = zacks_score['Value']['Text']
    ZACKS_VALUE_COLOR = zacks_score['Value']['Color']
    ZACKS_GROWTH_SCORE = zacks_score['Growth']['Score']
    ZACKS_GROWTH_TEXT = zacks_score['Growth']['Text']
    ZACKS_GROWTH_COLOR = zacks_score['Growth']['Color']


    # IN THE NEWS ======================================
    sentiment_tuple = news.get_sentiment(i)
    company_news_dict = news.get_company_news(i)

    COMPANY_MOOD = sentiment_tuple[0]
    COMPANY_MOOD_TEXT = sentiment_tuple[1]
    try:
        COMPANY_ARTICLE_0 = f'<a class="content_link" style="color: #000; overflow: hidden;font-size: 9px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;width: 200px;" target="_blank" href="{company_news_dict[0]["url"]}" >{company_news_dict[0]["short_title"]}</a>'
        COMPANY_ARTICLE_SOURCE_0 = company_news_dict[0]['source']
    except:
        COMPANY_ARTICLE_0 = f'<p class="content_link" style="color: #000; overflow: hidden;font-size: 9px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;width: 200px;">No news obtained</p>'
        COMPANY_ARTICLE_SOURCE_0 = ' '
    try:
        COMPANY_ARTICLE_1 = f'<a class="content_link" style="color: #000; overflow: hidden;font-size: 9px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;width: 200px;" target="_blank" href="{company_news_dict[1]["url"]}" >{company_news_dict[1]["short_title"]}</a>'
        COMPANY_ARTICLE_SOURCE_1 = company_news_dict[1]['source']
    except:
        COMPANY_ARTICLE_1 = ' '
        COMPANY_ARTICLE_SOURCE_1 = ' '

    try:
        COMPANY_ARTICLE_2 = f'<a class="content_link" style="color: #000; overflow: hidden;font-size: 9px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;width: 200px;" target="_blank" href="{company_news_dict[2]["url"]}" >{company_news_dict[2]["short_title"]}</a>'
        COMPANY_ARTICLE_SOURCE_2 = company_news_dict[2]['source']
    except:
        COMPANY_ARTICLE_2 = ' '
        COMPANY_ARTICLE_SOURCE_2 = ' '

    try:
        COMPANY_NEWS_SUMMARY = ' '
        # COMPANY_NEWS_SUMMARY = news.get_gpt_summary(i, company_news_dict, sentiment_tuple)
    except:
        COMPANY_NEWS_SUMMARY = ' '


    #endregion ================================== --------------------------------

    try:
        for user in users:
            should_notify = False
            if send_report_admin_only:
                should_notify = True
            else:
                #check if current ticker (i) is in user's watchlist
                if i in user['watchlist']:
                    ticker_settings = user['watchlist'][i]
                    triggers = ticker_settings.get("triggers", {})

                    # region CHECK TRIGGERS
                    if triggers.get("daily_report", False):
                        should_notify = True

                    # STOCK PRICE MODULE ------------------
                    # today's price is lower than last month
                    if (triggers.get("daily_below_last_month", False) and DAILY_PRICE < LOW_LAST_MONTH):
                        should_notify = True
                    # today's price is lower than 90 days
                    if triggers.get("daily_below_ninety", False) and DAILY_PRICE < NINETY_DAY:
                        should_notify = True
                    # today's price is lower than prev 365 days
                    if triggers.get("daily_below_365", False) and DAILY_PRICE < LOWEST_IN_YEAR:
                        should_notify = True
                    # if stock price is lower than a certain amount
                    stock_price_trigger = triggers.get("stock_price", False)
                    if stock_price_trigger:
                        if DAILY_PRICE <= stock_price_trigger.get("lte", 0) or DAILY_PRICE >= stock_price_trigger.get("gte", 150000):
                            should_notify = True

                    # RSI MODULE -------------------------
                    # RSI is within user settings range
                    rsi_trigger = triggers.get("rsi", False)
                    if rsi_trigger and type(RSI_NUM) == float:
                        if RSI_NUM <= rsi_trigger.get("lte", 0) or RSI_NUM >= rsi_trigger.get('gte', 100):
                            should_notify = True


                    #endregion

            if should_notify:
                email = f'''
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>

<body style="font-family: Inter, Arial, sans-serif;color: #000;">  

<!-- STOCK NAME & CURRENT PRICE -->
<h3 style="font-weight: 400;">Stock Summary</h3>
  <h1 style="font-size: 42px;font-weight: 600;">{i}<span class="thin-h1" style="font-weight: 400; margin-left: 20px;">${DAILY_PRICE}</span></h1>


  <!-- PRICE TO EARNINGS -->
  <div class="space" style="height: 30px;"></div>
  <table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;text-align: left;">Price-to-Earnings</p>
      </td>
      <td class="buy_signal_box" style="width: 100px;border-radius: 20px;margin: auto 2px;">
        <!-- <h6 class="buy_signal_text" style="color: #505050;text-align: center;font-size: 11px;font-style: normal;font-weight: 600;line-height: 0;padding: 4px 10px;">Buy signal: </h6> -->
      </td>
    </tr>
    <tr>
      <td colspan="3">
        <div class="component_wrapper_2" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 10px;width: 145px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Today</p>
          <p class="content_price_2" style="font-size: 24px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{STOCK_PE}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;"> </p>

        </div>
        <div class="component_wrapper_2" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 10px;width: 145px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Industry Average</p>
          <p class="content_price_2" style="font-size: 24px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{INDUS_PE}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;"> </p>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <p class="descrip" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 0 10px 10px 10px;margin-top: 0px;">{PE_STATEMENT}</p>
      </td>
    </tr>
  </table>


<!-- RETURN ON EQUITY -->
  <div class="space" style="height: 30px;"></div>

  <table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;text-align: left;">Return on Equity</p>
      </td>
      <td class="buy_signal_box" style="width: 100px;border-radius: 20px;margin: auto 2px;">
        <!-- <h6 class="buy_signal_text" style="color: #505050;text-align: center;font-size: 11px;font-style: normal;font-weight: 600;line-height: 0;padding: 4px 10px;">Buy signal: -</h6> -->
      </td>
    </tr>
    <tr>
      <td colspan="3">
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">{RECENT_YEAR_DATE_ROE}</p>
          <p class="content_price_3" style="color: {RECENT_YEAR_COLOR_ROE};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{RECENT_YEAR_ROE}%</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">{PREV_YEAR_DATE_ROE}</p>
          <p class="content_price_3" style="font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{PREV_YEAR_ROE}%</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">{YEAR_BF_L_DATE_ROE}</p>
          <p class="content_price_3" style="font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{YEAR_BF_L_ROE}%</p>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <p class="descrip" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 0 10px 10px 10px;margin-top: 10px;">{ROE_STATEMENT}</p>
      </td>
    </tr>
  </table>



<!-- GROSS PROFIT MARGIN -->
  <div class="space" style="height: 30px;"></div>

  <table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;text-align: left;">Gross Profit Margin</p>
      </td>
      <td class="buy_signal_box" style="width: 100px;border-radius: 20px;margin: auto 2px;">
        <h6 class="buy_signal_text" style="color: #505050;text-align: center;font-size: 11px;font-style: normal;font-weight: 600;line-height: 0;padding: 4px 10px;">{BUY_SIGNAL_GPM}</h6>
      </td>
    </tr>
    <tr>
      <td colspan="3">
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Recent Q</p>
          <p class="content_price_3" style="color: {RECENT_Q_COLOR_GPM};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{RECENT_Q_GPM}%</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{RECENT_Q_DIFF_GPM}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">{RECENT_YEAR_DATE_GPM}</p>
          <p class="content_price_3" style="color: {RECENT_YEAR_COLOR_GPM};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{RECENT_YEAR_GPM}%</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{RECENT_YEAR_DIFF_GPM}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">{YEAR_BF_L_DATE_GPM}</p>
          <p class="content_price_3" style="color: {YEAR_BF_L_COLOR_GPM};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{YEAR_BF_L_GPM_NUMBER}%</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{YEAR_BF_L_DIFF_GPM}</p>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <p class="descrip_w_trending" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 10px 10px 10px 10px;margin-top: 0px;">{GPM_STATEMENT}</p>
      </td>
    </tr>
  </table>
  
  <!-- NET PROFIT MARGIN -->
  <div class="space" style="height: 30px;"></div>

  <table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;text-align: left;">Net Profit Margin</p>
      </td>
      <td class="buy_signal_box" style="width: 100px;border-radius: 20px;margin: auto 2px;">
        <h6 class="buy_signal_text" style="color: #505050;text-align: center;font-size: 11px;font-style: normal;font-weight: 600;line-height: 0;padding: 4px 10px;">{BUY_SIGNAL_NPM}</h6>
      </td>
    </tr>
    <tr>
      <td colspan="3">
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Recent Q</p>
          <p class="content_price_3" style="color: {RECENT_Q_COLOR_NPM};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{RECENT_Q_NPM}%</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{RECENT_Q_DIFF_NPM}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">{RECENT_YEAR_DATE_NPM}</p>
          <p class="content_price_3" style="color: {RECENT_YEAR_COLOR_NPM};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{RECENT_YEAR_NPM_NUMBER}%</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{RECENT_YEAR_DIFF_NPM}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">{YEAR_BF_L_DATE_NPM}</p>
          <p class="content_price_3" style="color: {YEAR_BF_L_COLOR_NPM};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{YEAR_BF_L_NPM_NUMBER}%</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{YEAR_BF_L_DIFF_NPM}</p>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <p class="descrip_w_trending" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 10px 10px 10px 10px;margin-top: 0px;">{NPM_STATEMENT}</p>
      </td>
    </tr>
  </table>
  
  <!-- RSI & GROWTH -->
  <div class="space" style="height: 30px;"></div>
  <table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title_2" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;width: 130px;text-align: left;">RSI</p>
      </td>
      <td>
        <p class="module_title_3" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 5px 0px 0px;width: 130px;text-align: left;">Growth Rate</p>
      </td>
    </tr>
    <tr>
      <td colspan="3">
        <div class="component_wrapper_2" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 145px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Today</p>
          <p class="content_price_2" style="font-size: 24px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{RSI_NUM}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{RSI_TRENDING}</p>
        </div>
        <div class="component_wrapper_2" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 145px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Rev Growth {RECENT_YEAR_DATE_ARG}</p>
          <p class="content_price_2" style="color: {COLOR_ARG};font-size: 24px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{RECENT_YEAR_ARG_NUMBER}%</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{ARG_TRENDING}</p>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <p class="descrip" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 0 10px 10px 10px;margin-top: 0px;"> </p>
      </td>
    </tr>
  </table>
  
<!-- STOCK PRICE MODULE -->
<div class="space" style="height: 30px;"></div>
<table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;text-align: left;">Stock Price</p>
      </td>
      <td class="buy_signal_box" style="width: 100px;border-radius: 20px;margin: auto 2px;">
        <h6 class="buy_signal_text" style="color: #505050;text-align: center;font-size: 11px;font-style: normal;font-weight: 600;line-height: 0;padding: 4px 10px;">{BUY_SIGNAL_STOCK}</h6>
      </td>
    </tr>
    <tr>
      <td colspan="3">
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">30-Day Low</p>
          <p class="content_price_3" style="font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">${LOW_LAST_MONTH}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{MONTH_DESCRIP}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">90-Day Low</p>
          <p class="content_price_3" style="font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">${NINETY_DAY}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{NINETY_DESCRIP}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">365-Day Low</p>
          <p class="content_price_3" style="font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">${LOWEST_IN_YEAR}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{YEAR_DESCRIP}</p>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <p class="descrip" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 0 10px 10px 10px;margin-top: 0px;"> </p>
      </td>
    </tr>
  </table>


<div class="space" style="height: 30px;"></div>

<h3 style="font-weight: 400;">Public Perception</h3>
<!-- Zacks -->

  <table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;text-align: left;">Zacks</p>
      </td>
    </tr>
    <tr>
      <td colspan="3">
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Zacks Rank</p>
          <p class="content_price_3" style="font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{ZACKS_RANKING}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{ZACKS_RANK_DESCRIP}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Value</p>
          <p class="content_price_3" style="color: {ZACKS_VALUE_COLOR};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{ZACKS_VALUE_SCORE}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{ZACKS_VALUE_TEXT}</p>
        </div>
        <div class="component_wrapper_3" style="display: inline-block;height: 55px;margin: 0 2px 0 2px;padding-bottom: 0px;width: 97px;">
          <p class="content_time" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 10px;">Growth</p>
          <p class="content_price_3" style="color: {ZACKS_GROWTH_COLOR};font-size: 18px;font-weight: 600;padding: 0 10px;margin: 15px 0 0 0;">{ZACKS_GROWTH_SCORE}</p>
          <p class="content_descrip" style="font-size: 11px;font-weight: 400;line-height: 1;padding: 0 5px 0 10px;margin-bottom: 0px;">{ZACKS_GROWTH_TEXT}</p>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <p class="descrip_w_trending" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 10px 10px 10px 10px;margin-top: 0px;">{ZACKS_STATEMENT}</p>
      </td>
    </tr>
  </table>
  
<div class="space" style="height: 30px;"></div>

<!-- In The News -->
  <table class="module_wrapper" style="border-collapse: collapse;border-spacing: 0;background-color: #F6F6F6;border-radius: 20px;height: 100px;width: 315px;">
    <tr>
      <td>
        <p class="module_title" style="font-size: 20px;font-style: normal;font-weight: 600;padding: 0 2px 0px 15px;text-align: left;">In The News</p>
      </td>
      <td class="buy_signal_box" style="width: 100px;border-radius: 20px;margin: auto 2px;">
        <h6 class="buy_signal_text" style="color: #505050;text-align: center;font-size: 11px;font-style: normal;font-weight: 600;line-height: 0;padding: 4px 10px;">Mood: {COMPANY_MOOD}</h6>
      </td>
    </tr>
    <tr>
      <td>
        {COMPANY_ARTICLE_0}      
        </td>
      <td>
        <p class="content_time_w_links" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 30px;">{COMPANY_ARTICLE_SOURCE_0}</p>
      </td>
    </tr>
    <tr>
      <td>
        {COMPANY_ARTICLE_1}
      </td>
      <td>
        <p class="content_time_w_links" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 30px;">{COMPANY_ARTICLE_SOURCE_1}</p>
      </td>
    </tr>
    <tr>
      <td>
        {COMPANY_ARTICLE_2}
      </td>
      <td>
        <p class="content_time_w_links" style="color: #858384;font-size: 10px;font-weight: 400;line-height: 0;padding: 0 0 0 30px;">{COMPANY_ARTICLE_SOURCE_2}</p>
      </td>
    </tr>
    <tr>
      <td colspan="2">
        <br style="height: 5px;">
        <p class="descrip" style="font-size: 11px;font-weight: 350;line-height: 1.4;padding: 0 10px 10px 10px;margin-top: 0px;">{COMPANY_MOOD_TEXT}: {COMPANY_NEWS_SUMMARY}</p>
      </td>
      
    </tr>
  </table>
</body>


<p style="font-size: 10px;font-weight: 300;line-height: 1.2;padding: 0 5px 0 10px;margin-bottom: 0px;">By accessing "Eat At The Buffet" newsletter, you agree to our <a style="color: #000" href="https://sophiecheung.notion.site/Terms-Conditions-bdc4af15f4504074956862c5872f9ac5?pvs=4">Terms of Service</a>. Our content is not financial or investment advice, but a reflection of financial analysis based on data extracted through Yahoo Finance, AlphaVantage, Zacks and other investment platforms. Data is subjected to change or may be inccurate and not in control of Eat At The Buffet.</p>


  </body>
  </html>
'''

                send_email.send_email(i, user['email'], email)
                print(f'sent {i} to {user["email"]}')
                time.sleep(59) # sends 1 stock per minute

    except Exception as e:
        print(f'Error processing ticker {i} for user {user["email"]}: {e}')