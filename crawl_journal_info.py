import requests
import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from collections import namedtuple
from requests.adapters import HTTPAdapter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import logging
import csv

base_url = 'http://search.cnki.com.cn/'
journal_url = 'CJFD/Detail/Index/' # YWZG
volume_base_url = 'cjfd/Home/Detail/'#YWZG202004
JournalInfo = namedtuple('JournalInfo', 'journal_code name publisher ISSN')

def get_url_content(url, time=30):
    r = requests.get(url, timeout=time)
    html = r.content
    html_doc = html.decode("utf-8","ignore")
    url_decode = BeautifulSoup(html_doc, features="lxml")
    return url_decode

def get_journal_info(journal_name):
    search_journal_info = 'http://search.cnki.com.cn/cjfd/Home/CorrelationCjfd?Name=' + journal_name + '&Issn=&Cn=&KeyWd=&Unit=&PublicAddress=&Page=1'
    search_res = get_url_content(search_journal_info)
    print(search_journal_info)
    try:
        journal_pageurl = search_res.find('a', attrs={'title':journal_name})['href']
        journal_CODE = journal_pageurl[-4:]
        content = get_url_content('http:' + journal_pageurl)
        journal_info = content.find_all('div', attrs={'class':'r-line'})[0].find_all('span')
        journal_PUB = journal_info[0].text.split('：')[1]
        journal_ISSN = journal_info[1].text.split('：')[1]
    except Exception:
        print("Cannot Find " + journal_name)
        journal_CODE = ''
        journal_PUB = ''
        journal_ISSN = ''
    return JournalInfo(journal_code=journal_CODE, name=journal_name, publisher=journal_PUB, ISSN=journal_ISSN)

def write_journal_info_to_disk(journal_info_list, name):
    f = open(os.path.join('journal_info',name + '_j_info.csv'),'w',encoding='utf-8')
    w = csv.writer(f)
    #'docid title url author journal_code year abstract'
    w.writerow(('journal_code', 'name', 'publisher', 'ISSN'))    # field header
    w.writerows([(data.journal_code, data.name, data.publisher, data.ISSN) for data in journal_info_list])
    f.close()

if __name__ == "__main__":
    JR = '自然资源与环境'
    f = open('journal_info/'+ JR +'.txt','r')
    journal_list = f.readlines()
    journal_list = [i.strip() for i in journal_list]
    f.close()
    journal_info_list = []
    for i in journal_list:
        journal_info_list.append(get_journal_info(i))
        time.sleep(random.randint(0,2))
    write_journal_info_to_disk(journal_info_list, JR)