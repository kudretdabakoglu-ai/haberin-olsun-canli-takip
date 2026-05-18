#!/usr/bin/env python3
"""
Haberin Olsun — Tarama Scripti (GitHub Actions)
Sonuçları docs/results.json dosyasına kaydeder.
"""

import requests, json, os, time
from datetime import datetime, timezone

GETX_API_KEY = os.environ["GETX_API_KEY"]
FRESH_HOURS  = 6
ACCOUNTS     = [
    "bpthaber", "pusholder", "bosunatiklama",
    "haskologlu", "gusholderhaber", "HaberReport", "ajansoteki"
]
PRIORITY_SOURCES = {"bpthaber", "pusholder"}

def get_tweets(username, limit=20):
    try:
        r = requests.get(
            "https://api.getxapi.com/twitter/user/tweets",
            headers={"Authorization": f"Bearer {GETX_API_KEY}"},
            params={"userName": username, "limit": limit},
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("tweets", [])
        print(f"  [{username}] HTTP {r.status_code}")
    except Exception as e:
        print(f"  [{username}] Hata: {e}")
    return []

def content_fit(text):
    t = text.lower()
    x03 = ["spotify","netflix","disney","hollywood","oscar","nba","nfl","premier lig",
           "la liga","bundesliga","barcelona","real madrid","liverpool","manchester",
           "arsenal","chelsea","elon musk","chatgpt","taylor swift"]
    x05 = ["akp ","chp ","mhp ","dem parti","hdp ","muhalefet ","iktidar "]
    x25 = ["gözaltına alındı","tutuklandı","operasyon","yolsuzluk","skandal","rüşvet",
           "zimmet","hayatını kaybetti","iddianame","savcılık","milyon tl","milyar tl",
           "enflasyon","zam ","usulsüzlük","dolandırıcı"]
    x20 = ["haksız","rezalet","şoke","rekor kırdı","ihale","imar rantı"]
    x15 = ["deprem","yangın","trafik kazası","galatasaray","fenerbahçe","beşiktaş",
           "trabzonspor","dolar","euro","faiz","kira ","bakan","milletvekili"]
    for kw in x03:
        if kw in t: return 0.3
    for kw in x05:
        if kw in t: return 0.5
    for kw in x25:
        if kw in t: return 2.5
    for kw in x20:
        if kw in t: return 2.0
    for kw in x15:
        if kw in t: return 1.5
    return 1.0

def elazig_bonus(text):
    t = text.lower()
    if any(kw in t for kw in ["elazığspor","elazig spor","gakgoş","gakgos"]): return 2.0
    if any(kw in t for kw in ["elazığ","elazig","harput","fırat üniversitesi"]): return 1.8
    return 1.0

def risk_filter(text):
    t = text.lower()
    if any(kw in t for kw in ["intihar","çocuk istismarı","cinsel saldırı"]): return 0.1
    if any(kw in t for kw in ["iddia edildi","doğrulanamadı","asılsız"]): return 0.5
    return 1.0

def calc_score(tw, username):
    try:
        td = datetime.strptime(tw["createdAt"], "%a %b %d %H:%M:%S +0000 %Y").replace(tzinfo=timezone.utc)
        age_h = max((datetime.now(timezone.utc) - td).total_seconds() / 3600, 0.25)
    except:
        age_h = 1.0
    raw  = tw.get("likeCount",0) + tw.get("retweetCount",0)*2 + tw.get("replyCount",0) + tw.get("quoteCount",0)
    views = max(tw.get("viewCount",1), 1)
    velocity  = raw / age_h
    eng_rate  = (raw / views) * 100
    eng_boost = min(0.8 + eng_rate * 0.12, 1.4)
    text = tw.get("text","")
    src_mult   = 1.4 if username.lower() in PRIORITY_SOURCES else 1.0
    is_breaking = "son dakika" in text.lower() or "#sondakika" in text.lower()
    break_mult = 1.3 if is_breaking else 1.0
    score = round(velocity * content_fit(text) * elazig_bonus(text) * src_mult * break_mult * eng_boost * risk_filter(text))
    return score, age_h, is_breaking

def scan():
    results = []
    for acc in ACCOUNTS:
        print(f"  → @{acc}")
        for tw in get_tweets(acc, limit=20):
            try:
                td = datetime.strptime(tw["createdAt"], "%a %b %d %H:%M:%S +0000 %Y").replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - td).total_seconds() / 3600 > FRESH_HOURS:
                    continue
            except:
                continue
            score, age_h, is_breaking = calc_score(tw, acc)
            results.append({
                "username":    acc,
                "text":        tw.get("text",""),
                "url":         tw.get("url",""),
                "score":       score,
                "age_h":       round(age_h, 1),
                "is_breaking": is_breaking,
                "is_priority": acc.lower() in PRIORITY_SOURCES,
                "likes":       tw.get("likeCount", 0),
                "retweets":    tw.get("retweetCount", 0),
                "views":       tw.get("viewCount", 0),
            })
        time.sleep(0.5)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]

if __name__ == "__main__":
    print(f"Tarama başlıyor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    results = scan()
    print(f"{len(results)} haber bulundu")
    output = {
        "scan_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scan_time_tr": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "count": len(results),
        "results": results
    }
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("results.json kaydedildi.")
