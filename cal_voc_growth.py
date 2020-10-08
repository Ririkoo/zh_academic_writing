#!/usr/bin/env python
# coding: utf-8

import pickle
import pkuseg
import csv
import os
import re
import opencc
from tqdm import tqdm
from tqdm import tqdm_notebook
from functools import cmp_to_key
from collections import namedtuple
from zhon.hanzi import punctuation as cn_punctuation
from string import punctuation as en_punctuation
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit


work_dir = '/Users/pzhe/Documents/2020_Spring/FAH-Research/Voc'
ArticleInfo = namedtuple('ArticleInfo', 'docid title url author journal_code year abstract')
ArticleSEGInfo = namedtuple('ArticleSEGInfo', 'docid title url author journal_code year seg_abstract')
os.chdir(work_dir)
converter = opencc.OpenCC('t2s.json')

POSTAG = False
seg = pkuseg.pkuseg(postag=POSTAG)

def clean_str_for_win(str):
    str = str.encode("utf-8", "ignore").decode("utf-8")
    str = str.replace('\r', '')
    str = str.replace('\n', ';')
    return str

def write_journal_articles_to_disk(base_info_list, journal):
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

def clean_and_seg(text, is_contact=False, is_POS=False):
    text = text.strip()
    if(text.find('<正>')!=-1):
        text = text.replace('<正>','')
    seg_text = seg.cut(text)
    remove_punc = []
    for seg_word in seg_text:
        if (is_POS):
            if (seg_word[0] not in cn_punctuation) and (seg_word[0] not in en_punctuation):
                remove_punc.append(seg_word[0] + '/' + seg_word[1])
        else:
            if (seg_word not in cn_punctuation) and (seg_word not in en_punctuation):
                remove_punc.append(seg_word)
    if is_contact:
        return ' '.join(remove_punc)
    else:
        return remove_punc
    
def read_journal_info_from_disk(full_path):
    with open(full_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        info_list = [ArticleInfo(docid=row[0], 
                                 title=row[1], 
                                 url=row[2], 
                                 author=row[3], 
                                 journal_code=row[4],
                                year=row[5],
                                seg_abstract=clean_and_seg(row[6]), is_contact=True) for row in reader]
    return info_list

def read_journal_from_pkl(journal_file):
    import pickle
    f = open(os.path.join('base_csv/语言学', journal_file), 'rb')
    info_list = pickle.load(f)
    f.close()
    return info_list

def filter_announcement(string):
    
    key_words = ['召开会议', '征稿', '召开', '学术研讨会', '学术讨论会', '开幕', '闭幕']
    if string == '' or string is None:
        return True
    for i in key_words:
        if string.find(i) != -1:
            return True
    return False

# Heaps Law
def heaps(N, a, C):
    return a * (N**C)

# Guiraud's Methods
def guiraud(N, r):
    return r * np.sqrt(N)

# Hubert-Labbes
def sum_Nf(Nf, u):
    sum = 0
    for i in Nf:
        sum += Nf[i]*((1-u)**i)
    return sum

def fit_hubert(x_data, p):
    u,sigma = x_data
    return p*u*word_count + (1-p)*(word_count - sigma)

if __name__ == "__main__":
    # all_file_list = os.listdir('base_csv/语言学')
    # file_list = [i for i in all_file_list if (i.split('.')[-1] == 'csv')]
    # all_article_info = []

    # for i in pkl_file_list:
    #     all_article_info += read_journal_from_pkl(i)

    # ## Read from tupled pkl 
    # info_list = []
    # invalid_cnt = 0
    # for info in tqdm(all_article_info):
    #     if filter_announcement(info.abstract):
    #         invalid_cnt+=1
    #         continue
    #     else:
    #         info_list.append(ArticleSEGInfo(docid=info.docid, 
    #                                 title=info.title, 
    #                                 url=info.url, 
    #                                 author=info.author, 
    #                                 journal_code=info.journal_code,
    #                                 year=info.year,
    #                                 seg_abstract=clean_and_seg(info.abstract, is_contact=True, is_POS=POSTAG)))
    with open('seg_info.pkl','rb') as f:
        seg_info_list = pickle.load(f)
    sorted_seg_infolist = sorted(seg_info_list, key=lambda x:x.year)
    year_tw = {}
    year_Nf = {}
    SAMPLE_POINT = 1000
    passage_count = 0
    LENGTH = len(sorted_seg_infolist)

    words = {} # dictionary with word as key and frequency as value
    Nf = {} # dictionary with frequency as key and number of types with that given frequency (freq. of freq.) as value
    token_words = {}
    count = 0
    word_count = 0
    token_count = 0

    for idx,info in enumerate(tqdm(sorted_seg_infolist)):
        passage_count += 1
        words_collection = info.seg_abstract.split()
        if info.year not in year_tw:
            year_tw[info.year] = [0,0]
        for word in words_collection:
            token_count += 1
            word = converter.convert(word.strip())
            if not word in words:
                words[word] = 0
                word_count += 1
            if words[word] in Nf:
                Nf[ words[word] ] -= 1
            words[word] += 1
            if words[word] in Nf:
                Nf[ words[word] ] += 1
            else:
                Nf[ words[word] ] = 1
            if idx<LENGTH-1:
                if info.year!=sorted_seg_infolist[idx+1].year:
                    year_tw[info.year] = [token_count, word_count]
                    year_Nf[info.year] = words.copy()
            elif idx==LENGTH-1:
                year_tw[info.year] = [token_count, word_count]
                year_Nf[info.year] = words.copy()
            if (token_count%SAMPLE_POINT == 0):
                token_words[token_count] = [word_count, Nf.copy()]
        word_count = len(words)
    
    N, V = zip(*token_words.items())
    real_V = [i[0] for i in V]

    popt, pcov = curve_fit(heaps, N, real_V)
    a = popt[0]
    C = popt[1]
    print("Heaps' Model: |V|=a(N^C)\nvalue of a = %f"%a)
    print("value of C = %f"%C)
    heaps_pred = heaps(N, *popt)

    popt, pcov = curve_fit(guiraud, N, real_V)
    r = popt[0]
    print("Guiraud's Model: r = %f"%r)
    guiraud_pred = guiraud(N, r)


    y_data = []
    x_data_u = []
    x_data_sigma = []
    print('Preprocessing for H-L Method')
    for i in tqdm(token_words):
        y_data.append(token_words[i][0])
        # u=n/N, sigma
        u = i/token_count
        x_data_u.append(u)
        x_data_sigma.append(sum_Nf(token_words[i][1], u))
    h_popt, h_pcov = curve_fit(fit_hubert, (x_data_u, x_data_sigma), y_data)
    p_pred = h_popt[0]
    print("H-L Model : value of p = %f" % p_pred)
    hubert_pred = [fit_hubert((x_data_u[i], x_data_sigma[i]), p_pred) for i in range(0,len(x_data_u))]
    