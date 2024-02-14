import requests
from bs4 import BeautifulSoup
import pandas

# in this document, we scrap FullRatio and their table and turn their industry pe into a dictionary
# the dictionary can be accessed through the var pm_dict
# the pandas part does nothing, but could help w pretty print
# if this returns as an error, use the csv
# Update the CSV only when data updates


# SCRAP FOR INDUSTRY PE
url = 'https://fullratio.com/profit-margin-by-industry'
response = requests.get(url)
html = response.text
soup = BeautifulSoup(html, 'html.parser')
table = soup.find_all("table")
# print(table)
#
td = table[0].find_all("td")

pm_dict = {}
for i in range(0, len(td), 4):
    name = td[i].text.strip().replace('-', '_')
    gross_pm = float(td[i+1].text.strip('%'))
    if td[i+2].text.strip() == 'N/A':
        net_pm = '-'
    else:
        net_pm = float(td[i+2].text.strip('%'))
    if name not in pm_dict:
        pm_dict[name] = {}
    pm_dict[name]['gpm'] = gross_pm
    pm_dict[name]['npm'] = net_pm


# DICTIONARY WITH PROFIT MARGINS HERE
# print(pm_dict)


# pretty print with pandas
# profit_margin = pandas.DataFrame.from_dict(pm_dict, orient='index')
# profit_margin.columns = ['Avg Gross Profit Margin', 'Avg Net Profit Margin']
# profit_margin.index.name = 'Industry'
# print(profit_margin)

# to CSV
# profit_margin.to_csv('profit_margin.csv')