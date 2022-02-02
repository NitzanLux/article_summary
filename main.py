# import requests
import os
import argparse
import requests
import bs4
from bs4 import BeautifulSoup
import re
from typing import List
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import random
import urllib
import lxml

NUMBER_OF_CITATION_PER_PAGE = 10
CITE_BY_MATCH = re.compile("Cited by [0-9]+")


def open_page(url):
    # headers = {
    #     "User-Agent": "Selenium/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36"}
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
        'referer': 'https://www.google.com/'}

    # page = requests.get(url,headers=headers)
    time.sleep(1.2)
    print("url:  ", url)

    page = requests.get(url, headers=headers)
    print("loaded")
    assert page.status_code == 200, "cannot load page"
    return page


def join_url_with_article_name(article_name: str):
    base_str = f"https://scholar.google.com/scholar?q={urllib.parse.quote_plus(article_name)}&hl=en&as_sdt=0"
    return base_str


def get_first_result_citations(page: requests.Response) -> str:
    soup = BeautifulSoup(page.content, 'html.parser')
    first_search = list(soup.find_all('div', class_="gs_ri"))
    first_search = first_search[0]
    html_links = first_search.find_all('a')
    link = None
    for html_link in html_links:
        if CITE_BY_MATCH.match(html_link.get_text()):
            link = "https://scholar.google.com" + html_link['href']
            break
    else:
        assert False, "didn't find citation link"
    return link


def get_citations_pdf_html_links(citation_link) -> List[str]:
    page = open_page(citation_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    class_link_html_iter = soup.find_all('div', class_='gs_or_ggsm')
    links = []
    for class_link in class_link_html_iter:
        if len(links) > NUMBER_OF_CITATION_PER_PAGE:
            break
        links.append(class_link.find_all('a')[0]['href'])
    return links


def get_all_citations_pdf_html_links(citation_link: str) -> List[str]:
    scholar_page = "https://scholar.google.com/scholar?"
    link_with_page = lambda page_number, scholar_page=scholar_page, citation_link=citation_link: \
        scholar_page + "start={page_number}&".format(
            page_number=page_number * NUMBER_OF_CITATION_PER_PAGE) + citation_link[len(scholar_page):]
    cur_citation_links = []
    citation_links_list = []
    flag = True
    counter = 0
    while flag or len(cur_citation_links) > 0:
        cur_citation_links = get_citations_pdf_html_links(link_with_page(counter))
        citation_links_list.extend(cur_citation_links)
        counter += 1
    return citation_links_list


def get_citation_from_pdf(article_name: str, url: str):
    page = open_page(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    all_article_citation = soup.find_all(class_="title")
    # all_article_citation = [(i.parent,type(i.parent)) for i in all_article_citation]

    out = find_citation_from_citations_section(all_article_citation[0])
    print(out)


def get_citation_from_science_direct(article_name: str, url: str):
    page = open_page(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    citations_names = soup.find_all('strong')
    # citations_names_values = [i['value'] for i in citations_names]
    # all_article_citation = [(i.parent,type(i.parent)) for i in all_article_citation]
    # all_article_citation = all_article_citation.find_all(text=article_name)
    # out = find_citation_from_citations_section(all_article_citation[0])
    print(citations_names)


def find_citation_from_citations_section(tag: bs4.element.Tag):
    link = []
    shut_down_counter = 10
    while (len(link) == 0):
        tag = tag.parent
        print(tag)
        link = list(tag.find_all("a"))

        assert shut_down_counter >= 0, "cannot find in the given parent"
        shut_down_counter -= 1
    return [i['href'] for i in link]


def get_article_citations(article_name: str):
    scholar_url = join_url_with_article_name(article_name)
    scholar_page = open_page(scholar_url)
    citation_link = get_first_result_citations(scholar_page)
    links = get_all_citations_pdf_html_links(citation_link)
    print(len(links))
    print(links)
    # return scholar_page


# %%

article_citations = get_article_citations(
    "Scalable Hierarchical Aggregation Protocol (SHArP): A Hardware Architecture for Efficient Data Reduction")

# get_citation_from_science_direct("An efficient analytical reduction of detailed nonlinear neuron models","https://www.sciencedirect.com/science/article/pii/S0896627321005018")
# %%
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
import io
import requests


def convert_pdf_to_txt(url):
    response = requests.get(url)
    fp = io.BytesIO(response.content)
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching,
                                  check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue()

    fp.close()
    device.close()
    retstr.close()
    return strip_text_from_breaks(text)


def strip_text_from_breaks(text):
    text = re.sub("-\n[\s]*", "", text)
    return re.sub("[\s]+", " ", text)


def get_cite_match(text, article_name):
    pattern = re.compile(f".+([\[\(])([\d]+)([\]\)]).+{re.escape(strip_text_from_breaks(article_name))}.+$")
    return pattern.match(text)


article_name = "Scalable Hierarchical Aggregation Protocol (SHArP): A Hardware Architecture for Efficient Data Reduction"
url = 'https://dl.acm.org/doi/pdf/10.1145/3152434.3152461'
txt = convert_pdf_to_txt(url)
m = get_cite_match(txt, article_name)
start_braces, cite_number, end_braces = m.groups()[0:3]
txt = txt[:m.start(1)]


def get_match_idx(subsring, text):
    return [(m.start(0), m.end(0)) for m in re.finditer(subsring, text)]
