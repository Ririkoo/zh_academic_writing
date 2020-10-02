# -*- encoding: utf-8 -*-

import os
import time
import csv
import random
import logging
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
# from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from collections import namedtuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


base_url = 'https://search.cnki.com.cn/'
tmp_f = open('basejs.js', 'r', encoding='utf8')
base_js = tmp_f.readlines()[0].strip()
tmp_f.close()
journal_url = 'CJFD/Detail/Index/'  # YWZG
volume_base_url = 'cjfd/Home/Detail/'  # YWZG202004
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/875.1.15 (KHTML, like Gecko) Version/18.0.3 Safari/965.1.15"

HEADERS = {
    'User-Agent': user_agent,
}
SESS = requests.Session()
SESS.mount('http://', HTTPAdapter(max_retries=10))
SESS.mount('https://', HTTPAdapter(max_retries=10))


JournalInfo = namedtuple('JournalInfo', 'journal_code name publisher ISSN')
ArticleInfo = namedtuple('ArticleInfo', 'docid title url author journal_code year abstract')
ArticleBaseInfo = namedtuple('ArticleBaseInfo', 'title url author journal_code vol')


def get_url_content(url, header=HEADERS, time=30):
    r = SESS.get(url, headers=header, timeout=time)
    html = r.content
    html_doc = html.decode("utf-8", "ignore")
    url_decode = BeautifulSoup(html_doc, features="lxml")
    return url_decode


# Get all article url
def get_article_by_year(year_list, volume_list_base, DRIVER):
    article_tot_year = []
    cnt = 0
    # Get unique volume url each year
    volume_years_url = [volume_list_base + str(year) for year in year_list]
    # Get unique article url each year
    for year_url in volume_years_url:
        r = SESS.get(year_url, headers=HEADERS, timeout=30)
        html = r.content
        html_doc = html.decode("utf-8", "ignore")
        url_decode = BeautifulSoup(html_doc, features="lxml")
        vol_url_list = url_decode.find_all('a')
        # print(vol_url_list)
        if cnt != 0 and cnt % 10 == 0:
            logging.info("sleep 60s per 10 years")
            time.sleep(60)
        DRIVER.delete_all_cookies()
        article_single_year = crawl_current_year_all(vol_url_list, driver=DRIVER)
        time.sleep(random.randint(0, 6))
        article_tot_year += article_single_year
        cnt += 1
    return article_tot_year

def complie_js(base_js, journal_code, pub_year, issue):
    base_js.replace('JOURNAL_CODE_PLACEMENT', journal_code)
    base_js.replace('PUB_YEAR_PLACEMENT', pub_year)
    base_js.replace('ISSUE_PLACEMENT', issue)
    return base_js

def crawl_current_year_all(vol_url_list, driver):
    article_info = []
    full_vol_url_list = [base_url[:-1] + vol_list['href'] for vol_list in vol_url_list]
    journal_code = vol_url_list[0]['href'].split('/')[-1][0:4]
    pub_year = vol_url_list[0]['href'].split('/')[-1][4:8]
    pub_issues = [vol_list['href'].split('/')[-1][-2:] for vol_list in vol_url_list]
    try:
        driver.get(full_vol_url_list[0])
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, './/div[@class="tab-left"]')))
    except Exception as e:
        logging.error(e)
        logging.info("Timeout")
        time.sleep(30)
    response_json = None
    for idx, issue in enumerate(pub_issues):
        logging.info("Crawling " + full_vol_url_list[idx])
        get_catalog_js = complie_js(base_js, journal_code, pub_year, issue)
        try:
            response_json = driver.execute_script(get_catalog_js)
        except Exception as e:
            logging.error(e)
            logging.info("Error, sleep 33")
            time.sleep(33)
        time.sleep(random.randint(1, 2))
        if response_json is not None:
            for section in response_json:
                for article_info_json in section['QiKanCatalog']:
                    if article_info_json['Author'] != '':
                        article_info.append(
                            ArticleInfo(docid=article_info_json['FileName'],
                                        title=article_info_json['Title'],
                                        url=article_info_json['TargetUrl'],
                                        author=article_info_json['Author'],
                                        journal_code=article_info_json['FileName'][0:4],
                                        year=article_info_json['Year'],
                                        abstract=article_info_json['Summary']))
    print(len(article_info))
    logging.info(len(article_info))
    return article_info


def read_journal_info_from_disk(domain):
    with open(os.path.join('journal_info', domain + '_j_info.csv'), 'r', encoding='utf8') as csvfile:
        reader = csv.reader(csvfile)
        info_list = [JournalInfo(journal_code=row[0], name=row[1], publisher=row[2], ISSN=row[3]) for row in reader]
    return info_list

def clean_str_for_win(str):
    str = str.encode("utf-8", "ignore").decode("utf-8")
    str = str.replace('\r', '')
    str = str.replace('\n', ';')
    return str

def write_journal_articles_to_disk(base_info_list, journal):
    import pickle
    try:
        with open(os.path.join('base_csv', journal + '.pkl'),'wb') as pklf:
            pickle.dump(base_info_list, pklf)
    except Exception as e:
        logging.info(e)
    f = open(os.path.join('base_csv', journal + '_full_info.csv'), 'w', encoding='utf-8')
    w = csv.writer(f)
    # 'docid title url author journal_code year abstract'
    w.writerow(('docid', 'title', 'url', 'author', 'journal_code', 'year', 'abstract'))  # field header
    w.writerows([(clean_str_for_win(data.docid),
                  clean_str_for_win(data.title),
                  clean_str_for_win(data.url),
                  clean_str_for_win(data.author),
                  clean_str_for_win(data.journal_code),
                  data.year, clean_str_for_win(data.abstract)) for data in base_info_list])
    f.close()


def crawl_singel_jornal(journal):
    logger = logging.getLogger()
    fhandler = logging.FileHandler(filename='log/' + journal.journal_code + '.log', mode='a')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)
    logger.setLevel(logging.INFO)
    init_url = base_url + journal_url + journal.journal_code
    url_decode = get_url_content(init_url)
    # Get journal publised years
    year_list_str = url_decode.find('div', attrs={"class": "part03"}).find_all('span')[1:]
    year_list = [int(year.text[0:4]) for year in year_list_str]
    # Gernerate volume base url
    options = webdriver.ChromeOptions()
    # forbid loading the pictures and css for saving the time
    prefs = {"profile.managed_default_content_settings.images": 2, 'permissions.default.stylesheet': 2}
    options.add_experimental_option("prefs", prefs)
    selenium_driver = webdriver.Chrome(chrome_options=options)
    selenium_driver.delete_all_cookies()
    volume_list_base = 'http://search.cnki.com.cn/CJFD/Detail/CJFDResult?PYKM=' + journal.journal_code + '&Page=10&Year='  # 2020
    article_tot_year = get_article_by_year(year_list, volume_list_base, selenium_driver)
    logging.info('Write journal ' + journal.name)
    write_journal_articles_to_disk(article_tot_year, journal.name)



if __name__ == "__main__":
    journal_info_list = read_journal_info_from_disk('历史学')
    # Crawl journal - Batch Mode
    START_POINT = 0
    END_POINT = len(journal_info_list)
    for i in range(START_POINT, END_POINT):
        logging.info('== Start crawling journal ' + journal_info_list[i].name)
        crawl_singel_jornal(journal_info_list[i])
        logging.info('== End crawling journal ' + journal_info_list[i].name)
        logging.info('Pause 1000s')
        time.sleep(1000)