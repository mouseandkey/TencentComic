import requests
import re
import execjs
import json
import os
import concurrent.futures

# 如果要下载付费章节，需要登录账号购买，替换上自己购买了的账号就好了
# 如果爬取的是免费的漫画，可以不需要headers
# 关键是cookie
headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "max-age=0",
    "cookie": "",
    "referer": "https://ac.qq.com/Comic/comicInfo/id/645332?_via=pc.index.vippay6",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}

# 从漫画详情页获取每个章节的地址
def get_chapter_list(url):
    resp = requests.get(url, headers=headers)
    title = re.search("<title>(.*?)</title>", resp.text).group()
    print("你要下载的漫画是：" + title[7:title.index("-")])
    chapter_list = re.findall("<span class=\'works-chapter-item\'>(.*?)</span>", resp.text.replace("\r\n", " "))

    return chapter_list

# 进入每个章节，获取章节的内容
def get_chapter(chapter):
    while True:
        url = 'https://ac.qq.com' + re.search('href=\"(.*?)\"', chapter).group()[6:-1]
        resp = requests.get(url, headers=headers)
        url_title = re.findall("<title>《(.*?)》(.*?)-.*?</title>", resp.text)
        print(url_title[0][1])
        try:
            html = resp.text
            data = re.findall("(?<=var DATA = ').*?(?=')", html)[0]   # 提取DATA
            nonce = re.findall('window\[".+?(?<=;)', html)[1]   # 提取window["no"+"nce"]
            nonce = '='.join(nonce.split('=')[1:])[:-1]   # 掐头去尾
            nonce = execjs.eval(nonce)   # 通过execjs模块计算js代码
        except:
            print("没有解析出nonce")
            continue

        # js逆向
        T = list(data)
        N = re.findall('\d+[a-zA-Z]+', nonce)
        jlen = len(N)
        while jlen:
            jlen -= 1
            jlocate = int(re.findall('\d+', N[jlen])[0]) & 255
            jstr = re.sub('\d+', '', N[jlen])
            del T[jlocate:jlocate + len(jstr)]
        T = ''.join(T)
        try:
            _v = json.loads(bytes(base(T)))
        except UnicodeDecodeError:
            print("编码出错了")
            continue
        break

    # print(_v)
    return _v

# 计算解密
def base(T):
    keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    a = []
    e = 0
    while e < len(T):
        b = keyStr.index(T[e])
        e += 1
        d = keyStr.index(T[e])
        e += 1
        f = keyStr.index(T[e])
        e += 1
        g = keyStr.index(T[e])
        e += 1
        b = b << 2 | d >> 4
        d = (d & 15) << 4 | f >> 2
        h = (f & 3) << 6 | g
        a.append(b)
        if 64 != f:
            a.append(d)
        if 64 != g:
            a.append(h)

    return a

# 根据图片地址下载图片
def get_pic(url, path, cSeq, i):
    f = open(f'{path}/{cSeq}-{i}.jpg', 'wb')
    f.write(requests.get(url).content)
    f.close()

if __name__ == '__main__':
    comic_id = input("请输入漫画编号：")
    url = f'https://ac.qq.com/Comic/comicInfo/id/{comic_id}'
    chapter_list = get_chapter_list(url)
    cont = input("是否继续下载？(y/n)")
    if cont == "y":
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(get_chapter,chapter) for chapter in chapter_list]
            for future in concurrent.futures.as_completed(futures):
                data = future.result()
                cSeq = data['chapter']['cSeq']
                path = f"D://漫画/{data['comic']['title']}/{cSeq}-{data['chapter']['cTitle']}"
                if not os.path.exists(path):
                    os.makedirs(path)
                    print(f"{data['comic']['title']}/{cSeq}-{data['chapter']['cTitle']}")
                for i in range(len(data['picture'])):
                    executor.submit(get_pic, data['picture'][i]['url'], path, cSeq, i)

    elif cont == "n":
        pass
    else:
        print("警告：请输入正确的选项！(y/n)")
