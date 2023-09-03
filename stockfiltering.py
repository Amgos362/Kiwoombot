from bs4 import BeautifulSoup as bs
import time
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pymysql
import pandas as pd
import openpyxl

def crawl_and_filter(driver, url, df_real):
    driver.get(url)
    time.sleep(5)
    dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "select#currentPageSize")))
    select = Select(dropdown)
    select.select_by_value('100')
    button = driver.find_element_by_xpath("//a[@onclick='fnSearch1();return false;']")
    button.click()
    time.sleep(5)
    html = driver.page_source
    soup = bs(html, 'lxml')
    garbage = soup.find_all('td', class_="first")
    gwanli = [item.text.strip() for item in garbage]
    df_real = remove_unwanted_companies(df_real, gwanli)
    return df_real

def remove_unwanted_companies(df, unwanted_companies):
    return df[~df['name'].isin(unwanted_companies)]

def remove_specific_words(df, words):
    for word in words:
        df = df[~df['name'].str.contains(word)]
    return df

driver = webdriver.Chrome()
conn = pymysql.connect(host='127.0.0.1', user='root', password='Quantum45**', db='INVESTAR', charset='utf8')
sql = "SELECT code, name, total FROM company_info"
df_total = pd.read_sql(sql, conn)
sql = "SELECT code, date, close FROM daily_price"
df_close = pd.read_sql(sql, conn)
df_close['date'] = pd.to_datetime(df_close['date'])
df_close = df_close[df_close['date'] == '2023-06-30']
df = pd.merge(df_total, df_close, on='code')
df['market_cap'] = df['total'] * df['close']
df_real = df[df['market_cap'] > 100000000000] # 시가총액 1000억 이상

url_list = ['https://kind.krx.co.kr/investwarn/adminissue.do?method=searchAdminIssueList',
            'https://kind.krx.co.kr/investwarn/hwangiissue.do?method=searchHwangiIssueMain',
            'https://kind.krx.co.kr/investwarn/tradinghaltissue.do?method=searchTradingHaltIssueMain',
            'https://kind.krx.co.kr/investwarn/undisclosure.do?method=searchUnfaithfulDisclosureCorpList',
            'https://kind.krx.co.kr/corpgeneral/delistRealInvstg.do?method=searchDelistRealInvstgMain',
            'https://kind.krx.co.kr/investwarn/investattentEmbezzlement.do?method=searchInvestAttentEmbezzlementMain']

for url in url_list:
    df_real = crawl_and_filter(driver, url, df_real)

word_list = ["KODEX", "ARIRANG", "TIGER", "KBSTAR", "ACE", "KOSEF", "HANARO", "SOL"]
df_real = remove_specific_words(df_real, word_list)
codes = df_real['code']
codes.to_excel('real_codes.xlsx', index=False)

print(codes)
driver.quit()

