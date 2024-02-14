import requests
from bs4 import BeautifulSoup

# in this document, we scrap Eqvista and their table and turn their industry pe into a dictionary
# the dictionary can be accessed through the var pe_dict
# the pandas part does nothing, but could help w pretty print
# if this returns as an error, use the csv


# SCRAP FOR INDUSTRY PE
url = 'https://eqvista.com/price-to-earnings-pe-ratios-by-industry/'
response = requests.get(url)
html = response.text
soup = BeautifulSoup(html, 'html.parser')
table = soup.find_all("tbody")
# print(table)

industry_name = table[0].find_all("td", {"class": "column-1"})
pe = table[0].find_all("td", {"class": "column-2"})

pe_dict = {}

for i, j in zip(industry_name, pe):
    name = i.text.strip()
    pe_ratio = j.text.strip()
    pe_dict[name] = pe_ratio

# PE ratio by industry here
# print(pe_dict)

# pretty print with pandas
# industry_pe = pandas.DataFrame([pe_dict]).transpose()
# industry_pe.columns = ['PE Ratio']
# industry_pe.index.name = 'Industry'
# print(industry_pe)

# to CSV
# industry_pe.to_csv('industry_pe.csv')

