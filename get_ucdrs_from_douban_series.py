import os
import re
import sys

from datetime import datetime

import requests
from lxml import etree

import time

import subprocess

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36"
}

title_isbn_path=r"D:\get_ucdrs_links_from_douban_series\title_isbns.txt"
info_link_path=r"D:\get_ucdrs_links_from_douban_series\info_links.txt"

already_path=r"D:\get_ucdrs_links_from_douban_series\already_buy.txt"

visited_pages_path=r"D:\get_ucdrs_links_from_douban_series\visited_pages.txt"

today_buy_path=r"D:\get_ucdrs_links_from_douban_series\today_buy.txt"

bookmarks_path=r"C:\Users\linsi\AppData\Local\CentBrowser\User Data\Default\Bookmarks"

folder_name="丛书"

def get_links(folder_name):
    with open(bookmarks_path,"r",encoding="utf-8") as f:
        bookmarks=f.readlines()

    idx=len(bookmarks)-1

    pivot1=f"\"name\": \"{folder_name}\""
    pivot2="\"children\""

    flag=2

    while idx!=-1 and flag>0:
        each_line=bookmarks[idx]
        if pivot1 in each_line:
            last_idx=idx
            flag=1
        if flag==1 and pivot2 in each_line:
            fst_idx=idx
            flag=0
        idx-=1

    # print(f"fst_idx:{fst_idx};last_idx:{last_idx}")

    bookmarks_s="".join(bookmarks[fst_idx:last_idx])

    # print(bookmarks_s)

    patt_id="\"name\":\s\"(.*?)\""
    patt_url="\"url\":\s\"(.*?)\""

    ids=re.findall(patt_id,bookmarks_s)
    urls=re.findall(patt_url,bookmarks_s)

    print(f"ids:{ids}")
    print(f"urls:{urls}")

    # return tuple(zip(ids,urls))

    return urls

def choose_series_id(urls):
    num_in=input("Use Prefix i for index(1 base), e.g. i3 -> urls[2]\nOr plain number for series_id ")
    if num_in.isdigit():
        series_id=num_in
    elif num_in.startswith("i") and num_in[1:].isdigit():
        url=urls[int(num_in[1:])-1]
        assert "series" in url
        if "page" in url:
            url=url.split("?page=")[0]
        series_id=url.rsplit("/",maxsplit=1)[1]

    print ("Series ID:", series_id)
    return series_id

def get_max_page_num(series_id):
    douban_series_link=f'https://book.douban.com/series/{series_id}'
    page_text=requests.get(douban_series_link,headers=headers).text
    html=etree.HTML(page_text)
    max_page_patt="//div[@class='paginator']/a[contains(@href,'?page=')][last()]//@href"
    find=html.xpath(max_page_patt)

    if find:
        find=find[0]
        print("find as",find)
        max_page_num=find.rsplit("=",maxsplit=1)[1]
        assert max_page_num.isdigit()
    else:
        print("Not found")
        max_page_num='1'

    print("Max page num:",max_page_num)
    return max_page_num

def get_pages_links(series_id,max_page_num):
    boilerplate_link='https://book.douban.com/series/'
    series_link=f"{boilerplate_link}{series_id}"
    print("Max page num:",max_page_num)

    with open(visited_pages_path,"r",encoding="utf-8") as f:
        visited_pages=[each.rsplit("?page=",maxsplit=1)[-1].strip("\n") for each in f.readlines() if series_link in each]

    print("Already visited:",visited_pages)

    num_in=input("input the pages you want; split by ,(discrete) or -(continue)\n")
    if "," in num_in:
        page_ids=num_in.split(",")
        print("page ids:",page_ids)
        pages_links=[f"{series_link}?page={page_id}" for page_id in page_ids]
    elif "-" in num_in:
        start_page,end_page=num_in.split("-")
        print(f"start at {start_page}; end at {end_page}")
        page_ids=[each_id for each_id in range(int(start_page),int(end_page)+1)]
        pages_links = [f"{series_link}?page={page_id}" for page_id in page_ids]
    elif num_in.isdigit():
        page_ids=[num_in]
        pages_links = [f"{series_link}?page={page_id}" for page_id in page_ids]

    print ("[Pages Links]:")
    for each_link in pages_links:
        print(each_link)

    return pages_links

def get_subject_links(page_link):
    page_text=requests.get(page_link,headers=headers).text
    html=etree.HTML(page_text)
    subject_patt="//a[@class='nbg']//@href"
    links=html.xpath(subject_patt)

    print("[subject links]:")
    for each_idx,each_link in enumerate(links,1):
        print(f"{each_link}\t\t{each_idx}")

    return links

def get_title_isbn(subject_link):
    page_text=requests.get(subject_link,headers=headers).text
    html=etree.HTML(page_text)
    isbn_patt="//div[@id='info']//text()"
    finds=html.xpath(isbn_patt)

    title_patt="//head/title//text()"

    title=html.xpath(title_patt)[0].replace(" (豆瓣)","")


    # print(finds)

    # info_s="".join(finds)
    # print("Info:",info_s)

    isbn_idx=len(finds)-1

    isFound=0

    while not isFound:
        item=finds[isbn_idx].strip()
        if item.startswith("978"):
            isbn=item
            isFound=1
        isbn_idx-=1
        if isbn_idx==-1 and not isFound:
            print("isbn not found!")
            return None

    print("title:",title)
    print("isbn:",isbn)


    with open(title_isbn_path,"a",encoding="utf-8") as f:
        f.write(f"title: {title}\t\tisbn: {isbn}\n")
        print("title_isbn written.")

    return title,isbn

def get_ucdrs_links(some_isbn,title):
    ucdrs_template="http://book.ucdrs.superlib.net/search?Field=all&channel=search&sw="
    url=f"{ucdrs_template}{some_isbn}"
    page_text=requests.get(url,headers=headers).text
    html=etree.HTML(page_text)

    ucdrs_link_patt="//input[starts-with(@id,'url')]//@value"
    ssid_patt="//input[starts-with(@id,'ssid')]//@value"

    links=html.xpath(ucdrs_link_patt)
    ssids=html.xpath(ssid_patt)

    ssids_links={ssid:link for ssid,link in zip(ssids,links) if ssid!=""}
    print(ssids_links)

    if ssids==[""] or bool(ssids)==0 or ssids_links=={}:
        return []

    info_patt_node="//span[@class='fc-green']"
    ssid_info_nodes = html.xpath (info_patt_node)

    ssid_infos=[]

    for each_node in ssid_info_nodes:
        info=each_node.xpath("string(.)")
        print("info: ",info)
        ssid_infos.append(info)

    # 匹配单个标签下的所有内容
    # https://blog.csdn.net/t8116189520/article/details/80367549

    # 这样不管它是先出现 dxid 还是 先出现 ssid， 都可以顺利处理了!



    # ssid_infos2=[]
    # # 这个数字可以设得很大...

    # print("before ssid_info,",ssid_infos)

    # for each in range(1,100):
    # # 注意这里是>=，逻辑细节！！
    #     if len(ssid_infos)>=8*each:
    #         ssid_info="".join(ssid_infos[8*(each-1):8*each])
    #         ssid_infos2.append(ssid_info)
    #     else:
    #         break
    # ssid_infos=ssid_infos2
    # ssid_infos=ssid_infos[0:len(ssids)]

    print("ssids:\t",ssids)
    print("ssid-infos:\t",ssid_infos)

    option_idx=0

    for each_idx,each_info in enumerate(ssid_infos,1):
        if ssids[each_idx-1]:
            print(each_info,"\t\t\t",each_idx)
            option_idx=each_idx-1
    if len(ssids_links)==1:
        choice_idxs=[option_idx]
    elif len(ssids_links)>=2:
        choice_idxs_in=input("Your choice(multiple is ok, split by ,):")
        choice_idxs=[int(each)-1 for each in choice_idxs_in.split(",")]

    ucdrs_links=[]

    for choice_idx in choice_idxs:
        choose_info=ssid_infos[choice_idx]
        choose_ssid=ssids[choice_idx]
        ucdrs_link=ssids_links[choose_ssid]
        ucdrs_links.append(ucdrs_link)
        print("ucdrs link:",ucdrs_link)
        with open(info_link_path,"a",encoding="utf-8") as f:
            datetime_now=datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
            f.write(f"\n--- {datetime_now} ---\n")
            f.write("\n--- start ---\n")
            f.write(f"Title: {title}\nInfo: {choose_info}\nLink: {ucdrs_link}")
            f.write("\n--- end ---\n")

    return ucdrs_links

# get_ucdrs_links("9787214158116","cc")
# sys.exit(0)

    # 确实是逐个对应的！
    # print('links',links)
    # print('links len',len(links))r
    # print('ssids',ssids)
    # print('ssids len',len(ssids))

# get_ucdrs_link("白夜行")
# sys.exit(0)




# import requests



def main():

    already_set=set()
    with open(already_path,"r",encoding="utf-8") as f:
        already_set=set([each.strip("\n") for each in f.readlines() if each!="\n"])

    # print(already_set)
    # sys.exit(0)

    links=get_links(folder_name)
    series_id=choose_series_id(links)
    max_page_num=get_max_page_num(series_id)
    pages_links=get_pages_links(series_id,max_page_num=max_page_num)

    ucdrs_links=[]

    for page_link in pages_links:
        subject_links=get_subject_links(page_link)
        for subject_link in subject_links:
            title,isbn=get_title_isbn(subject_link)
            inner_ucdrs_links=get_ucdrs_links(isbn,title)
            if inner_ucdrs_links==[]:
                continue
            for ucdrs_link in inner_ucdrs_links:
            # sys.exit(0)
                if ucdrs_link in already_set:
                    continue
                else:
                    ucdrs_links.append(ucdrs_link)

    ucdrs_links_s="\n".join(ucdrs_links)

    with open(already_path,"a",encoding="utf-8") as f:
        f.write("\n")
        f.write(ucdrs_links_s)
        f.write("\n")

    with open(today_buy_path,"a",encoding="utf-8") as f:
        f.write("\n")
        f.write(ucdrs_links_s)
        f.write("\n")

    print("all done.")

    pages_links_s="\n".join(pages_links)

    with open(visited_pages_path,"a",encoding="utf-8") as f:
        f.write("\n")
        f.write(pages_links_s)
        f.write("\n")


if __name__ == '__main__':
    main()

