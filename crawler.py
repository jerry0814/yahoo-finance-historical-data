# -*- coding: utf-8 -*-
"""
Created on Fri Feb 2 2018

@author: Yue Peng
"""

import os
import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from collections import OrderedDict
import time
import random
import urllib3
import codecs
# import pymongo
urllib3.disable_warnings()

# check the existence of data directory
if not os.path.exists("data"):
    os.makedirs("data")
    print("Finishing creating data folder.\n")


# #####################S & P 100 Stock Prices###########################
class YahooCrawler:

    def __init__(self, url):
        self.url = url

    def change_format(self, symbols):
        """
            change the format matching the yahoo finance searching pattern
        """
        return list(map(lambda x: x.replace('.', '-'), symbols))

    def get_symbol_name(self):
        """
            scrapy the symbol table from wikipedia
        """
        with requests.Session() as s:
            response = s.get(self.url)
        content = response.content.decode("utf-8")
        soup = BeautifulSoup(content, "lxml")
        # extract the symbol table
        table_list = soup.find("table", {"class": "wikitable sortable"})
        # string processing
        table = list(filter(lambda a: a != "\n", list(table_list)))
        table = list(map(lambda x: "".join(str(x).split()), table))
        symbols, names = [], []
        for _, v in enumerate(table):
            try:
                begin = re.search(r"\<td\>", v).span()[1]
                end = re.search(r"\<\/td\>", v).span()[0]
                symbols.append(v[begin:end])
            except Exception:
                continue
        for _, v in enumerate(table):
            try:
                begin = re.search(r"title=\"", v).span()[1]
                end = re.search(r"\"\>", v).span()[0]
                names.append(v[begin:end])
            except Exception:
                continue
        symbols = self.change_format(symbols)
        return symbols, names

    def data_frame(self, symbols, names):
        """
            create a dataframe with symbols and names
        """
        table = OrderedDict({"Symbol": symbols, "Name": names})
        return pd.DataFrame(table, index=None)

    # Unix time converter
    def datetime_timestamp(self, dt):
        """
            convert the time into unix time
        """
        time.strptime(dt, '%Y-%m-%d %H:%M:%S')
        s = time.mktime(time.strptime(dt, '%Y-%m-%d %H:%M:%S'))
        return str(int(s))

    def get_cookie_crumb(self, symbol):
        """
            obtain the cookie and crumb from the yahoo website
        """
        url = "https://finance.yahoo.com/quote/%s/history?p=%s" % (symbol, symbol)
        response = requests.get(url)
        # get cookies
        cookie = dict(B=response.cookies["B"])
        # get crumb
        line = response.text.strip().replace('}', '\n')
        lines = line.split("\n")
        for l in lines:
            if re.findall(r'CrumbStore', l):
                crumb = l
        crumb = crumb.split(":")[2].strip('"')

        return cookie, crumb

    def download_csv(self, symbol, begin, end):
        """
            download the csv file on website
        """
        cookie, crumb = self.get_cookie_crumb(symbol)
        url2 = "https://query1.finance.yahoo.com/v7/finance/download/%s?period1=%s&period2=%s&interval=1d&events=history&crumb=%s" % (
            symbol, begin, end, crumb)
        with requests.Session() as s:
            r = s.get(url2, cookies=cookie, verify=False)
        with codecs.open(r"%s/data/%s.csv" % (os.getcwd(), symbol), "w", "utf-8") as f:
            f.write(r.text)
        print("Finished download %s.csv" % (symbol))

    def file_size(self, file_path):
        """
        this function will return the file size
        """
        if os.path.isfile(file_path):
            file_info = os.stat(file_path)
            return file_info.st_size

    def check(self):
        """
            re-download the failed csv file
        """
        # Load previous table
        with codecs.open(r"%s/%s.csv" % (os.getcwd(), "wiki_table"), "r", "utf-8") as f:
            df = pd.read_csv(f)
        symbols = df.Symbol.tolist()
        # check .csv file if null or not
        null_symbols = [1]
        while len(null_symbols):
            null_symbols = []
            for symbol in symbols:
                file_path = r"%s/data/%s.csv" % (os.getcwd(), symbol)
                if self.file_size(file_path) < 1000:
                    null_symbols.append(symbol)

            begin = self.datetime_timestamp("2017-02-02 09:00:00")
            end = self.datetime_timestamp("2018-02-02 09:00:00")
            for _, v in enumerate(null_symbols):
                self.download_csv(v, begin, end)
                time.sleep(10 + random.uniform(0, 1) * 20)

    def main(self):
        """
            solve the first part of yahoo problem.
        """
        # begin = datetime_timestamp(input("""Please enter the begin time like "2017-01-01 09:00:00\"\n"""))
        # end = datetime_timestamp(input("""Please enter the end time like "2018-01-01 09:00:00\"\n"""))
        begin = self.datetime_timestamp("2017-02-02 09:00:00")
        end = self.datetime_timestamp("2018-02-02 09:00:00")
        symbols, names = self.get_symbol_name()
        df = self.data_frame(symbols, names)
        df.to_csv(r"%s/%s.csv" % (os.getcwd(), "wiki_table"), index=None)
        for _, v in enumerate(symbols):
            self.download_csv(v, begin, end)
            time.sleep(10 + random.uniform(0, 1) * 20)

    def addcols(self):
        """
            preprocessing the bash file.
        """
        with codecs.open(r"%s/%s.csv" % (os.getcwd(), "wiki_table"), "r", "utf-8") as f:
            df = pd.read_csv(f)
        symbols = df.Symbol.tolist()
        for symbol in symbols:
            file_path = r"%s/data/%s.csv" % (os.getcwd(), symbol)
            with codecs.open(file_path, "r", "utf-8") as f:
                df = pd.read_csv(f)
            df.insert(0, "Symbol", pd.Series(
                [symbol] * df.shape[0], index=df.index))
            df.to_csv(file_path, index=None)


# ######################Funding and Publications###################################
class PubMedCrawler:

    def __init__(self):
        self.names = self.name_process()

    def name_process(self):
        """
            deal with the name
        """
        data = pd.read_csv(r"%s/NIHHarvard.csv" % (os.getcwd()))
        # remove the T and F
        idx = []
        for i, v in enumerate(data.Activity.tolist()):
            if v.startswith("T") or v.startswith("F"):
                continue
            else:
                idx.append(i)
        research = data.iloc[idx, :]
        PI_name = research[research.columns.values[13]]
        # get the unique name
        PI_name = list(set(PI_name))
        # remove the middle name or init
        firstList = []
        tmpList = []
        lastList = []
        for i in PI_name:
            first, last = (re.split(r',\s', i)[0], re.split(r',\s', i)[1])
            firstList.append(first)
            tmpList.append(last)
        for j in tmpList:
            lastList.append(re.split(r'\s', j)[0])
        names = ["{0}, {1}".format(x, y) for x, y in zip(firstList, lastList)]
        return names

    def extract_num_pub(self):
        """
            web scrapying part
        """
        num_pub = []
        for _, v in enumerate(self.names):
            first, last = tuple(v.split(", "))
            url = "https://www.ncbi.nlm.nih.gov/pubmed/?term={0}%2C+{1}%5BAuthor%5D+AND+Harvard%5BAffiliation%5D".format(
                first, last)
            time.sleep(7)
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "lxml")
            # just one publication situation
            if soup.find("h3", {"class": "result_count"}) is None:
                num_pub.append(1)
                print(v, num_pub[-1])
                continue
            begin = str(soup.find("h3", {"class": "result_count"})).find("Items")
            end = str(soup.find("h3", {"class": "result_count"})).find("</h3")
            item = str(soup.find("h3", {"class": "result_count"}))[begin:end]
            num = []
            for _, s in enumerate(item.split(" ")):
                if s.isdigit():
                    num.append(s)
            num_pub.append(num[-1])
            print(v, num_pub[-1])
        # convert into integer
        num_pub = list(map(lambda x: int(x), num_pub))
        table = OrderedDict({"Name": self.names, "Number of Publications": num_pub})
        df = pd.DataFrame(table)
        # sort by name
        df.sort_values(by=["Name"], inplace=True)
        df.to_csv(r"%s/num_publication.csv" % (os.getcwd()), index=None)
        print("The csv file was saved in %s" % (os.getcwd()))


if __name__ == "__main__":
    print("First part downloading started...\n")
    start = time.time()
    yahoo = YahooCrawler("http://en.wikipedia.org/wiki/S%26P_100")
    yahoo.main()
    print("Downloading completed!\n")
    yahoo.check()
    print("There is no empty file, we are all set.\n")
    yahoo.addcols()
    print("Adding a column of the corresponding symbol finished!\n")
    print("First part was all done!\n")
    print("Elapsed time is %.2fs" % (time.time() - start))

    print("Second part begins...\n")
    start = time.time()
    pub_med = PubMedCrawler()
    pub_med.extract_num_pub()
    print("Elapsed time is %.2fs" % (time.time() - start))
    print("HW1 was all finished.")
