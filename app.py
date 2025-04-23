from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import datetime

app = Flask(__name__)

def scrape_travel_info(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.pac-group.net/"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    trip_block = soup.select_one('#TRIP_BLOCK')
    if not trip_block:
        return None, "找不到行程區塊，請確認網址是否正確"

    titles = trip_block.select('.day_title .sub_add_img')
    infos  = trip_block.select('.day-group + .info')
    if len(titles) != len(infos):
        return None, "行程天數與餐食區塊數量不符"

    days = []
    for title, info in zip(titles, infos):
        txt = title.get_text(strip=True)
        m = re.match(r'Day\s*(\d+)\s*(\d{4}/\d{2}/\d{2})\s*(.+)', txt)
        if m:
            day_idx, iso_date, route = m.groups()
            yyyy, mm, dd = iso_date.split('/')
            wd = ['一','二','三','四','五','六','日'][datetime.date(int(yyyy),int(mm),int(dd)).weekday()]
            date_fmt = f"{mm}/{dd}({wd}) DAY{day_idx}"
        else:
            date_fmt = txt
            route = ""

        meals = {"早餐":"無","中餐":"無","晚餐":"無"}
        for blk in info.select('.col-lg-3'):
            kind = blk.select_one('.bg')
            cont = blk.select_one('.text')
            if not kind or not cont: 
                continue
            k = kind.get_text(strip=True)
            v = cont.get_text("／", strip=True).replace("\n", "").strip()
            if '早' in k:   meals["早餐"] = v
            if '中' in k:   meals["中餐"] = v
            if '晚' in k:   meals["晚餐"] = v

        days.append({
            "日期": date_fmt,
            "景點": route.strip(),
            "早餐": meals["早餐"],
            "中餐": meals["中餐"],
            "晚餐": meals["晚餐"]
        })

    return days, "success"

def format_html_output(days):
    cards = []
    for d in days:
        cards.append(f'''
        <div class="card mb-4 shadow-sm">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">{d["日期"]}</h5>
                <small>{d["景點"]}</small>
            </div>
            <div class="card-body">
                <p class="mb-1"><strong>早餐：</strong>{d["早餐"]}</p>
                <p class="mb-1"><strong>中餐：</strong>{d["中餐"]}</p>
                <p class="mb-0"><strong>晚餐：</strong>{d["晚餐"]}</p>
            </div>
        </div>
        ''')
    return "\n".join(cards)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    if not url:
        return jsonify(status="error", message="請輸入網址")
    days, msg = scrape_travel_info(url)
    if not days:
        return jsonify(status="error", message=msg)
    return jsonify(status="success", html_output=format_html_output(days))

if __name__ == '__main__':
    app.run(debug=True)
