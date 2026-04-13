"""경제 뉴스 트래커 서버 — 무료/프로/맥스 플랜."""

import json
import os
import threading
import re
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(BASE_DIR, "channels.json")

# ──────────────────────────────────────────────
#  설정
# ──────────────────────────────────────────────

CATEGORY_FEEDS = {
    "economy": [
        ("구글 경제",     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 경제검색", "https://news.google.com/rss/search?q=%EA%B2%BD%EC%A0%9C+%ED%99%98%EC%9C%A8+%EA%B8%88%EB%A6%AC&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 증시",     "https://news.google.com/rss/search?q=%EC%A3%BC%EC%8B%9D+%EC%A6%9D%EC%8B%9C+%EC%BD%94%EC%8A%A4%ED%94%BC&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 유가",     "https://news.google.com/rss/search?q=%EC%9C%A0%EA%B0%80+%EC%9B%90%EC%9C%A0+%EA%B8%88%EA%B0%92&hl=ko&gl=KR&ceid=KR:ko"),
        ("한국경제",      "https://www.hankyung.com/feed/all-news"),
        ("매일경제",      "https://www.mk.co.kr/rss/30000001/"),
        ("연합뉴스경제",  "https://www.yonhapnewstv.co.kr/category/news/economy/feed/"),
    ],
    "politics": [
        ("구글 정치",     "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZ4ZERBU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 국회",     "https://news.google.com/rss/search?q=%EA%B5%AD%ED%9A%8C+%EC%97%AC%EB%8B%B9+%EC%95%BC%EB%8B%B9&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 대통령",   "https://news.google.com/rss/search?q=%EB%8C%80%ED%86%B5%EB%A0%B9+%EC%B2%AD%EC%99%80%EB%8C%80+%EC%A0%95%EC%B9%98&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 선거",     "https://news.google.com/rss/search?q=%EC%84%A0%EA%B1%B0+%ED%9B%84%EB%B3%B4+%EA%B3%B5%EC%B2%9C&hl=ko&gl=KR&ceid=KR:ko"),
        ("연합뉴스정치",  "https://www.yonhapnewstv.co.kr/category/news/politics/feed/"),
    ],
    "tech": [
        ("구글 기술",     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 AI",       "https://news.google.com/rss/search?q=AI+%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5+ChatGPT&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 반도체",   "https://news.google.com/rss/search?q=%EB%B0%98%EB%8F%84%EC%B2%B4+%EC%97%94%EB%B9%84%EB%94%94%EC%95%84+%EC%82%BC%EC%84%B1&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 스타트업", "https://news.google.com/rss/search?q=%EC%8A%A4%ED%83%80%ED%8A%B8%EC%97%85+IT+%ED%85%8C%ED%81%AC&hl=ko&gl=KR&ceid=KR:ko"),
    ],
    "world": [
        ("구글 세계",     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 전쟁",     "https://news.google.com/rss/search?q=%EC%A0%84%EC%9F%81+%EC%9A%B0%ED%81%AC%EB%9D%BC%EC%9D%B4%EB%82%98+%EC%9D%B4%EB%9E%80&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 외교",     "https://news.google.com/rss/search?q=%EC%99%B8%EA%B5%90+%EC%A0%95%EC%83%81%ED%9A%8C%EB%8B%B4+%ED%8A%B8%EB%9F%BC%ED%94%84&hl=ko&gl=KR&ceid=KR:ko"),
        ("연합뉴스국제",  "https://www.yonhapnewstv.co.kr/category/news/international/feed/"),
    ],
    "realestate": [
        ("구글 부동산",   "https://news.google.com/rss/search?q=%EB%B6%80%EB%8F%99%EC%82%B0+%EC%95%84%ED%8C%8C%ED%8A%B8+%EC%A0%84%EC%84%B8&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 청약",     "https://news.google.com/rss/search?q=%EC%B2%AD%EC%95%BD+%EB%B6%84%EC%96%91+%EC%9E%AC%EA%B1%B4%EC%B6%95&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 집값",     "https://news.google.com/rss/search?q=%EC%A7%91%EA%B0%92+%EC%A3%BC%ED%83%9D+%EB%A7%A4%EB%A7%A4&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 대출",     "https://news.google.com/rss/search?q=%EC%A3%BC%ED%83%9D%EB%8B%B4%EB%B3%B4%EB%8C%80%EC%B6%9C+DSR+LTV&hl=ko&gl=KR&ceid=KR:ko"),
    ],
    "entertainment": [
        ("구글 연예",     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 아이돌",   "https://news.google.com/rss/search?q=%EC%95%84%EC%9D%B4%EB%8F%8C+%EC%BC%80%EC%9D%B4%ED%8C%9D+%EC%BB%B4%EB%B0%B1&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 드라마",   "https://news.google.com/rss/search?q=%EB%93%9C%EB%9D%BC%EB%A7%88+%EC%98%81%ED%99%94+%EB%84%B7%ED%94%8C%EB%A6%AD%EC%8A%A4&hl=ko&gl=KR&ceid=KR:ko"),
    ],
    "sports": [
        ("구글 스포츠",   "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 야구",     "https://news.google.com/rss/search?q=KBO+%EC%95%BC%EA%B5%AC+%ED%94%84%EB%A1%9C%EC%95%BC%EA%B5%AC&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 축구",     "https://news.google.com/rss/search?q=%EC%B6%95%EA%B5%AC+EPL+%EC%B1%94%ED%94%BC%EC%96%B8%EC%8A%A4%EB%A6%AC%EA%B7%B8&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 농구",     "https://news.google.com/rss/search?q=NBA+%EB%86%8D%EA%B5%AC+KBL&hl=ko&gl=KR&ceid=KR:ko"),
    ],
    "health": [
        ("구글 건강",     "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 의학",     "https://news.google.com/rss/search?q=%EC%9D%98%ED%95%99+%EC%B9%98%EB%A3%8C+%EC%8B%A0%EC%95%BD+%EC%A7%88%EB%B3%91&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 다이어트", "https://news.google.com/rss/search?q=%EA%B1%B4%EA%B0%95+%EB%8B%A4%EC%9D%B4%EC%96%B4%ED%8A%B8+%EC%9A%B4%EB%8F%99+%EC%98%81%EC%96%91&hl=ko&gl=KR&ceid=KR:ko"),
    ],
    "religion": [
        ("구글 종교",     "https://news.google.com/rss/search?q=%EC%A2%85%EA%B5%90+%EA%B5%90%ED%9A%8C+%EC%82%AC%EC%B0%B0+%EB%AA%A9%EC%82%AC&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 기독교",   "https://news.google.com/rss/search?q=%EA%B8%B0%EB%8F%85%EA%B5%90+%EB%B6%88%EA%B5%90+%EC%B2%9C%EC%A3%BC%EA%B5%90&hl=ko&gl=KR&ceid=KR:ko"),
        ("구글 교회",     "https://news.google.com/rss/search?q=%EA%B5%90%ED%9A%8C+%EC%84%A0%EA%B5%90+%EC%98%88%EB%B0%B0+%EC%8B%A0%ED%95%99&hl=ko&gl=KR&ceid=KR:ko"),
    ],
}

def get_feeds(category="economy"):
    return CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["economy"])

TRENDS_URL = "https://trends.google.co.kr/trending/rss?geo=KR"

STOPWORDS = {
    "것","수","등","이","그","저","및","또","더","위","중","대한","통해","위해",
    "있는","하는","되는","없는","같은","오늘","내일","어제","올해","지난","최근",
    "현재","다시","뉴스","속보","단독","종합","업데이트","포토","영상","기자",
    "특파원","앵커","리포트","인터뷰","한국","국내","해외","세계","글로벌","전세계",
    "정부","대통령","나라","우리","모두","사람","가능","예상","전망","분석",
    "발표","확인","결정","시장","경제","만에","이후","가장","처음","결국",
    "때문","바로","기업","회사","이번","이날","관련","일보","신문","경향",
    "대비","사이","상승","하락","것으로","포인트",
}

ECON_RE = re.compile(
    r"코스피|코스닥|나스닥|S&P|다우|니케이|항셍"
    r"|환율|금리|기준금리"
    r"|유가|금값|원유|WTI|브렌트|천연가스"
    r"|부동산|아파트|전세|월세|분양|재건축|재개발"
    r"|한은|연준|Fed|ECB|IMF|OECD|기재부|금감원"
    r"|반도체|배터리|2차전지|방산|바이오"
    r"|삼성|SK|현대|LG|네이버|카카오|테슬라|엔비디아|애플"
    r"|미국|중국|일본|러시아|이란|우크라이나|북한|대만|인도"
    r"|ETF|채권|펀드|연금|ISA|IRA"
    r"|인플레|디플레|스태그플레이션|관세|무역전쟁|제재|수출|수입"
    r"|호르무즈|지정학|봉쇄|파산|폭락|폭등|급등|급락|트럼프"
)
KOREAN_WORD_RE = re.compile(r"[가-힣]{2,}")
SUFFIX_RE = re.compile(r"(에서|으로|에게|까지|부터|이다|하는|되는|했다|됐다|한다|된다)$")
NUM_UNIT_RE = re.compile(r"\d+[%조억만원달러엔위안배]")


# ──────────────────────────────────────────────
#  채널 설정 관리
# ──────────────────────────────────────────────

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"my_channel": None, "competitors": [], "category": "economy"}


def save_channels(data):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def channel_id_from_input(text):
    """URL이나 핸들에서 채널 ID를 추출한다."""
    text = text.strip()
    # 이미 UCxxxx 형식
    if text.startswith("UC") and len(text) == 24:
        return text
    # @핸들 형식 → RSS로 확인 불가, 핸들 그대로 저장
    if text.startswith("@"):
        return text
    # URL에서 추출
    if "youtube.com" in text:
        if "/channel/" in text:
            parts = text.split("/channel/")
            return parts[1].split("/")[0].split("?")[0]
        if "/@" in text:
            parts = text.split("/@")
            return "@" + parts[1].split("/")[0].split("?")[0]
    return text


def get_channel_rss_url(channel_id):
    """채널 ID로 RSS URL을 만든다."""
    if channel_id.startswith("@"):
        # 핸들은 직접 RSS 불가 → 페이지에서 채널 ID 추출 시도
        return None
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


# ──────────────────────────────────────────────
#  데이터 수집
# ──────────────────────────────────────────────

def fetch_url(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 NewsTracker/1.0"})
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean_html(text):
    return re.sub(r"<[^>]+>", "", text).strip() if text else ""


def parse_date(text):
    if not text:
        return datetime.now(KST)
    try:
        dt = parsedate_to_datetime(text)
        return dt.astimezone(KST)
    except Exception:
        try:
            # YouTube RSS는 ISO 형식
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(KST)
        except Exception:
            return datetime.now(KST)


def extract_keywords(title):
    keywords = set()
    for m in ECON_RE.finditer(title):
        keywords.add(m.group())
    for m in NUM_UNIT_RE.finditer(title):
        keywords.add(m.group())
    for m in KOREAN_WORD_RE.finditer(title):
        w = SUFFIX_RE.sub("", m.group())
        if len(w) >= 2 and w not in STOPWORDS:
            keywords.add(w)
    return list(keywords)


def fetch_feed(name, url):
    articles = []
    try:
        xml = fetch_url(url)
        root = ET.fromstring(xml)
        for item in root.iter("item"):
            title = clean_html(item.findtext("title", ""))
            if not title:
                continue
            articles.append({
                "title": title,
                "link": item.findtext("link", ""),
                "source": name,
                "pubDate": parse_date(item.findtext("pubDate")).isoformat(),
                "keywords": extract_keywords(title),
            })
    except Exception as e:
        print(f"  [WARN] {name} 실패: {e}")
    return articles


def fetch_all(category="economy"):
    all_articles = []
    errors = []
    feeds = get_feeds(category)
    for name, url in feeds:
        arts = fetch_feed(name, url)
        if arts:
            print(f"  [{name}] {len(arts)}건")
        else:
            errors.append(name)
        all_articles.extend(arts)

    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    unique.sort(key=lambda a: a["pubDate"], reverse=True)
    return unique[:500], errors


def fetch_trends():
    trends = []
    try:
        xml = fetch_url(TRENDS_URL)
        root = ET.fromstring(xml)
        from urllib.parse import quote
        for item in root.iter("item"):
            keyword = item.findtext("title", "")
            traffic = ""
            # 관련 뉴스 제목 수집 (카테고리 판별용)
            news_titles = []
            for child in item:
                if "approx_traffic" in child.tag:
                    traffic = child.text or ""
                if "news_item_title" in child.tag:
                    news_titles.append(child.text or "")
            # 하위 요소에서도 뉴스 제목 추출
            for ni in item.iter():
                if "news_item_title" in ni.tag and ni.text:
                    news_titles.append(ni.text)
            link = f"https://www.google.com/search?q={quote(keyword)}"
            if keyword:
                trends.append({
                    "keyword": keyword,
                    "traffic": traffic,
                    "link": link,
                    "news_titles": news_titles[:3],
                })
    except Exception as e:
        print(f"  [WARN] 구글 트렌드 실패: {e}")
    return trends


# 카테고리별 관련 키워드 (필터링용)
CATEGORY_KEYWORDS = {
    "economy": {"경제","주식","코스피","코스닥","환율","금리","유가","원유","금값","투자","ETF","채권","펀드","은행","증시","관세","무역","수출","수입","GDP","인플레","금융","부채","적자","흑자","배당","IPO","상장","기업","매출","영업이익","연준","한은","기재부"},
    "politics": {"정치","국회","대통령","여당","야당","선거","후보","공천","탄핵","법안","의원","장관","청와대","총리","검찰","경찰","수사","기소","재판","판결","헌법","민주당","국민의힘","개혁"},
    "tech": {"AI","인공지능","반도체","엔비디아","삼성전자","테슬라","애플","구글","챗봇","GPT","로봇","자율주행","클라우드","데이터","스타트업","앱","소프트웨어","IT","테크","배터리","전기차","양자"},
    "world": {"전쟁","우크라이나","러시아","이란","이스라엘","트럼프","바이든","중국","일본","대만","북한","NATO","외교","정상회담","미사일","핵","제재","호르무즈","팔레스타인"},
    "realestate": {"부동산","아파트","전세","월세","집값","분양","청약","재건축","재개발","대출","LTV","DSR","주담대","매매","임대","공급","입주","모기지","갭투자"},
    "entertainment": {"배우","드라마","영화","아이돌","케이팝","컴백","앨범","콘서트","예능","방송","넷플릭스","디즈니","웨이브","시청률","흥행","연기","감독","시상식","데뷔","뮤비"},
    "sports": {"야구","축구","농구","KBO","EPL","NBA","올림픽","월드컵","감독","선수","경기","승리","우승","홈런","골","리그","프로야구","국대","이적","FA"},
    "health": {"건강","병원","의사","치료","질병","암","약","수술","백신","전염병","다이어트","운동","영양","정신건강","우울증","코로나","의학","임상","FDA"},
    "religion": {"교회","사찰","목사","신부","스님","예배","기도","성경","불교","기독교","천주교","이슬람","종교","신학","선교","절","성당"},
}


def filter_trends_by_category(trends, category):
    """카테고리와 관련된 트렌드만 필터링."""
    if category not in CATEGORY_KEYWORDS:
        return trends

    cat_kws = CATEGORY_KEYWORDS[category]
    filtered = []
    for t in trends:
        # 키워드 자체가 매칭
        if any(kw in t["keyword"] for kw in cat_kws):
            filtered.append(t)
            continue
        # 관련 뉴스 제목에 매칭
        all_text = " ".join(t.get("news_titles", []))
        if any(kw in all_text for kw in cat_kws):
            filtered.append(t)
    return filtered


def filter_articles_by_category(articles, category):
    """카테고리와 무관한 기사를 걸러낸다."""
    if category not in CATEGORY_KEYWORDS:
        return articles

    cat_kws = CATEGORY_KEYWORDS[category]
    filtered = []
    for a in articles:
        title = a.get("title", "")
        if any(kw in title for kw in cat_kws):
            filtered.append(a)
    # 너무 적으면 전체 반환 (소스가 부족한 경우)
    return filtered if len(filtered) >= 5 else articles


# ──────────────────────────────────────────────
#  [PRO] 경쟁 채널 모니터링
# ──────────────────────────────────────────────

def fetch_youtube_channel(channel_id, name=""):
    """유튜브 채널의 최근 영상을 RSS로 가져온다."""
    videos = []
    rss_url = get_channel_rss_url(channel_id)
    if not rss_url:
        return videos
    try:
        xml = fetch_url(rss_url)
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
        channel_name = root.findtext("atom:title", name, ns) or name

        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns)
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            published = entry.findtext("atom:published", "", ns)
            video_id = entry.findtext("{http://www.youtube.com/xml/schemas/2015}videoId", "")

            videos.append({
                "title": title,
                "link": link,
                "videoId": video_id,
                "channel": channel_name,
                "channelId": channel_id,
                "pubDate": parse_date(published).isoformat(),
                "keywords": extract_keywords(title),
            })
    except Exception as e:
        print(f"  [WARN] 채널 {name or channel_id} 실패: {e}")
    return videos


def fetch_all_competitors():
    """등록된 경쟁 채널의 최근 영상을 모두 가져온다."""
    channels = load_channels()
    all_videos = []
    for comp in channels.get("competitors", []):
        vids = fetch_youtube_channel(comp["id"], comp.get("name", ""))
        if vids and not comp.get("name"):
            comp["name"] = vids[0].get("channel", comp["id"])
            save_channels(channels)
        all_videos.extend(vids)
        if vids:
            print(f"  [경쟁:{vids[0].get('channel', comp['id'])}] {len(vids)}편")

    all_videos.sort(key=lambda v: v["pubDate"], reverse=True)
    return all_videos


def fetch_my_channel():
    """내 채널의 최근 영상을 가져온다."""
    channels = load_channels()
    my = channels.get("my_channel")
    if not my:
        return []
    vids = fetch_youtube_channel(my["id"], my.get("name", ""))
    if vids and not my.get("name"):
        my["name"] = vids[0].get("channel", my["id"])
        save_channels(channels)
    return vids


# ──────────────────────────────────────────────
#  [PRO] 블루오션 탐지 + 맞춤 추천
# ──────────────────────────────────────────────

def analyze_blue_ocean(topics, competitor_videos, my_videos):
    """핫토픽 중 경쟁채널이 아직 안 다룬 주제를 찾는다."""
    # 경쟁 채널이 최근 3일간 다룬 키워드
    cutoff = datetime.now(KST) - timedelta(days=3)
    comp_keywords = set()
    for v in competitor_videos:
        try:
            pub = datetime.fromisoformat(v["pubDate"])
            if pub > cutoff:
                comp_keywords.update(v.get("keywords", []))
        except Exception:
            comp_keywords.update(v.get("keywords", []))

    # 내가 다룬 키워드
    my_keywords = set()
    for v in my_videos:
        my_keywords.update(v.get("keywords", []))

    # 각 핫토픽에 블루오션 태그 + 추천 점수
    for topic in topics:
        kw = topic["keyword"]
        covered_by_comp = kw in comp_keywords
        covered_by_me = kw in my_keywords

        topic["blue_ocean"] = not covered_by_comp
        topic["already_covered"] = covered_by_me

        # 추천 점수: 높을수록 좋음
        rec_score = topic["score"] * 10  # 기본: 소스 수
        if not covered_by_comp:
            rec_score += 30  # 블루오션 보너스
        if covered_by_me:
            rec_score -= 20  # 이미 다룸 패널티
        if topic["urgency"] == "NOW":
            rec_score += 25
        elif topic["urgency"] == "HOT":
            rec_score += 15
        elif topic["urgency"] == "WARM":
            rec_score += 5

        topic["rec_score"] = rec_score

    return topics


def get_recommendations(topics, limit=10):
    """추천 토픽을 점수순으로 정렬해서 반환한다."""
    scored = [t for t in topics if t.get("rec_score", 0) > 0]
    scored.sort(key=lambda t: -t["rec_score"])
    return scored[:limit]


# ──────────────────────────────────────────────
#  핫토픽 분석
# ──────────────────────────────────────────────

def analyze_topics(articles):
    cutoff = datetime.now(KST) - timedelta(hours=24)
    recent = []
    for a in articles:
        try:
            pub = datetime.fromisoformat(a["pubDate"])
            if pub > cutoff:
                recent.append(a)
        except Exception:
            recent.append(a)

    kw_map = {}
    for a in recent:
        for kw in a["keywords"]:
            if len(kw) < 2:
                continue
            kw_map.setdefault(kw, []).append(a)

    topics = []
    for kw, arts in kw_map.items():
        sources = list(set(a["source"] for a in arts))
        if len(sources) >= 2:
            dates = []
            for a in arts:
                try:
                    dates.append(datetime.fromisoformat(a["pubDate"]))
                except Exception:
                    pass
            earliest = min(dates) if dates else datetime.now(KST)
            hours = (datetime.now(KST) - earliest).total_seconds() / 3600

            if hours < 3:
                urgency = "NOW"
            elif hours < 6:
                urgency = "HOT"
            elif hours < 12:
                urgency = "WARM"
            else:
                urgency = "COOL"

            topics.append({
                "keyword": kw,
                "score": len(sources),
                "sources": sources,
                "urgency": urgency,
                "age_hours": round(hours, 1),
                "article_count": len(arts),
                "articles": [{"title": a["title"], "link": a["link"],
                              "source": a["source"], "pubDate": a["pubDate"]}
                             for a in arts[:8]],
                "blue_ocean": False,
                "already_covered": False,
                "rec_score": 0,
            })

    topics.sort(key=lambda t: (-t["score"], t["age_hours"]))
    return topics


# ──────────────────────────────────────────────
#  글로벌 캐시
# ──────────────────────────────────────────────

_cache = {}  # 카테고리별: _cache["economy"] = {articles, topics, ...}
_shared = {  # 카테고리 무관 공유 데이터
    "trends": [],
    "competitors": [],
    "my_videos": [],
    "last_updated": None,
}
_lock = threading.Lock()


def check_youtube_search(keyword):
    """유튜브에서 이 키워드를 실제로 검색하고 있는지 확인한다."""
    try:
        from urllib.parse import quote
        url = f"https://suggestqueries-clients6.youtube.com/complete/search?client=youtube&q={quote(keyword)}&hl=ko&gl=KR&ds=yt"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        # JSONP 응답 파싱: window.google.ac.h([["keyword",[["suggest1",...],...]]])
        # 추천 검색어 수로 검색 활성도 판단
        suggestions = text.count('","')
        return {
            "has_search": suggestions > 0,
            "suggestion_count": suggestions,
            "raw": text[:500] if suggestions > 0 else "",
        }
    except Exception:
        return {"has_search": False, "suggestion_count": 0, "raw": ""}


def enrich_topics_with_youtube(topics):
    """핫토픽에 유튜브 검색 데이터를 추가한다."""
    for topic in topics[:15]:  # 상위 15개만 (API 부담 줄이기)
        kw = topic["keyword"]
        yt = check_youtube_search(kw)
        topic["yt_search"] = yt["has_search"]
        topic["yt_suggestions"] = yt["suggestion_count"]
        # 유튜브 점수 반영
        if yt["has_search"]:
            topic["rec_score"] = topic.get("rec_score", 0) + yt["suggestion_count"] * 2
    return topics


def extract_news_trending(articles, limit=15):
    """뉴스 기사에서 가장 많이 언급된 키워드를 추출한다."""
    kw_count = {}
    for a in articles:
        seen = set()
        for kw in a.get("keywords", []):
            if len(kw) < 2 or kw in seen:
                continue
            seen.add(kw)
            kw_count[kw] = kw_count.get(kw, 0) + 1

    # 2번 이상 등장한 키워드만
    ranked = [(kw, cnt) for kw, cnt in kw_count.items() if cnt >= 2]
    ranked.sort(key=lambda x: -x[1])
    return [{"keyword": kw, "count": cnt, "traffic": f"{cnt}건"} for kw, cnt in ranked[:limit]]


def refresh_single(cat):
    """단일 카테고리 수집."""
    articles, errors = fetch_all(cat)
    articles = filter_articles_by_category(articles, cat)
    news_trending = extract_news_trending(articles)
    topics = analyze_topics(articles)
    topics = enrich_topics_with_youtube(topics)
    with _lock:
        _cache[cat] = {
            "articles": articles[:100],
            "topics": topics[:40],
            "recommendations": [],
            "news_trending": news_trending,
            "errors": errors,
        }
    return articles, topics


def refresh_cache():
    """현재 카테고리 먼저, 나머지는 이어서."""
    channels = load_channels()
    primary = channels.get("category", "economy")
    print(f"\n[{datetime.now(KST).strftime('%H:%M:%S')}] 수집 시작 (우선: {primary})")

    # 1) 현재 카테고리 먼저
    arts, topics = refresh_single(primary)
    print(f"  [{primary}] {len(arts)}건, 핫토픽 {len(topics)}개 *** 준비완료")

    # 2) 트렌드
    trends = fetch_trends()
    with _lock:
        _shared["trends"] = trends[:20]
        _shared["last_updated"] = datetime.now(KST).isoformat()

    # 3) [PRO] 경쟁 채널 + 내 채널
    comp_videos = []
    my_videos = []
    if channels.get("competitors"):
        print("  경쟁 채널 수집 중...")
        comp_videos = fetch_all_competitors()
    if channels.get("my_channel"):
        my_videos = fetch_my_channel()
        if my_videos:
            print(f"  [내채널:{my_videos[0].get('channel','')}] {len(my_videos)}편")

    with _lock:
        _shared["competitors"] = comp_videos[:50]
        _shared["my_videos"] = my_videos[:15]

    # 블루오션 적용 (현재 카테고리)
    if comp_videos or my_videos:
        with _lock:
            t = _cache[primary]["topics"]
        t = analyze_blue_ocean(t, comp_videos, my_videos)
        recs = get_recommendations(t)
        with _lock:
            _cache[primary]["topics"] = t
            _cache[primary]["recommendations"] = recs

    # 4) 나머지 카테고리 백그라운드 수집
    for cat in CATEGORY_FEEDS:
        if cat == primary:
            continue
        try:
            a2, t2 = refresh_single(cat)
            if comp_videos or my_videos:
                t2 = analyze_blue_ocean(t2, comp_videos, my_videos)
                with _lock:
                    _cache[cat]["topics"] = t2
                    _cache[cat]["recommendations"] = get_recommendations(t2)
            print(f"  [{cat}] {len(a2)}건")
        except Exception as e:
            print(f"  [{cat}] 실패: {e}")

    print(f"[{datetime.now(KST).strftime('%H:%M:%S')}] 전체 완료! ({len(_cache)}개 카테고리)")


def auto_refresh():
    import time
    while True:
        time.sleep(30 * 60)
        try:
            refresh_cache()
        except Exception as e:
            print(f"[ERROR] 자동 갱신 실패: {e}")


# ──────────────────────────────────────────────
#  [MAX] 대본/제목/썸네일 생성 (템플릿 기반)
# ──────────────────────────────────────────────

SCRIPT_TEMPLATES = {
    "economy": {
        "hook": "지금 {keyword} 때문에 난리입니다. 근데 뉴스에서 안 알려주는 게 하나 있어요.",
        "intro": "오늘은 {keyword}이(가) 왜 터졌는지, 그리고 이게 내 돈에 어떤 영향을 주는지 정리해보겠습니다.",
        "body": [
            "## 1. 무슨 일이 벌어졌나\n{articles}",
            "## 2. 왜 이게 중요한가\n- 내 월급/투자/부동산에 미치는 영향\n- 전문가들의 전망",
            "## 3. 지금 뭘 해야 하나\n- 구체적 행동 가이드\n- 주의할 점",
        ],
        "closing": "정리하면, {keyword} 상황은 아직 진행 중입니다. 다음 영상에서 후속 상황 전해드리겠습니다.",
    },
    "politics": {
        "hook": "{keyword}, 이게 왜 갑자기 이슈가 됐을까요?",
        "intro": "오늘은 {keyword} 사태의 배경과 앞으로의 전망을 정리해보겠습니다.",
        "body": [
            "## 1. 사건의 발단\n{articles}",
            "## 2. 각 진영의 입장\n- 여당 측\n- 야당 측\n- 전문가 분석",
            "## 3. 앞으로의 전망\n- 시나리오별 정리",
        ],
        "closing": "{keyword} 이슈, 상황이 바뀌면 바로 전해드리겠습니다.",
    },
    "default": {
        "hook": "{keyword}, 지금 모르면 늦습니다.",
        "intro": "오늘은 {keyword}에 대해 핵심만 정리해보겠습니다.",
        "body": [
            "## 1. 무슨 일인가\n{articles}",
            "## 2. 왜 중요한가\n- 핵심 포인트 정리",
            "## 3. 정리 및 전망\n- 앞으로 어떻게 될 것인가",
        ],
        "closing": "{keyword} 관련해서 새로운 소식 나오면 바로 전해드리겠습니다.",
    },
}

TITLE_FORMULAS = [
    '"{keyword}" 지금 난리난 진짜 이유',
    '{keyword}, 아무도 안 알려주는 충격적 진실',
    '"{keyword}" 터졌다... 지금 안 보면 늦습니다',
    '{keyword} 때문에 벌어진 일 (심각합니다)',
    '속보 | {keyword} 상황 총정리 (핵심만)',
]

THUMBNAIL_TEMPLATES = [
    {
        "layout": "충격형",
        "text_main": "{keyword}",
        "text_sub": "지금 난리",
        "style": "빨간 배경 + 흰 글씨 + 놀란 표정 인물",
        "colors": "빨강/검정/흰색",
    },
    {
        "layout": "경고형",
        "text_main": "{keyword}",
        "text_sub": "긴급 속보",
        "style": "검정 배경 + 노란 경고 텍스트 + 화살표",
        "colors": "검정/노랑/빨강",
    },
    {
        "layout": "숫자형",
        "text_main": "{keyword}",
        "text_sub": "3가지 핵심",
        "style": "파란 배경 + 큰 숫자 + 그래프 이미지",
        "colors": "남색/흰색/주황",
    },
]


def generate_script(keyword, category, articles):
    """핫토픽 키워드로 대본 초안을 생성한다."""
    tpl = SCRIPT_TEMPLATES.get(category, SCRIPT_TEMPLATES["default"])

    # 관련 기사 요약
    article_lines = ""
    for a in articles[:5]:
        article_lines += f"- {a.get('title', '')}\n  출처: {a.get('source', '')}\n"

    script = f"""# {keyword} — 대본 초안

## 훅 (0~5초)
{tpl['hook'].format(keyword=keyword)}

## 인트로 (5~30초)
{tpl['intro'].format(keyword=keyword)}

"""
    for section in tpl["body"]:
        script += section.format(keyword=keyword, articles=article_lines) + "\n\n"

    script += f"""## 클로징
{tpl['closing'].format(keyword=keyword)}

---
*이 초안은 템플릿 기반입니다. AI 대본 생성은 Max 플랜에서 지원됩니다.*
"""
    return script


def generate_titles(keyword):
    """제목 후보 5개를 생성한다."""
    return [f.format(keyword=keyword) for f in TITLE_FORMULAS]


def generate_thumbnails(keyword):
    """썸네일 프롬프트 3개를 생성한다."""
    return [{k: v.format(keyword=keyword) if isinstance(v, str) else v for k, v in t.items()} for t in THUMBNAIL_TEMPLATES]


# ──────────────────────────────────────────────
#  HTTP 서버
# ──────────────────────────────────────────────

class Handler(SimpleHTTPRequestHandler):

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/data":
            cat = params.get("category", ["economy"])[0]
            with _lock:
                cat_data = _cache.get(cat, _cache.get("economy", {}))
                result = {
                    "articles": cat_data.get("articles", []),
                    "topics": cat_data.get("topics", []),
                    "recommendations": cat_data.get("recommendations", []),
                    "errors": cat_data.get("errors", []),
                    "trends": cat_data.get("news_trending", []),
                    "google_trends": _shared.get("trends", []),
                    "competitors": _shared.get("competitors", []),
                    "my_videos": _shared.get("my_videos", []),
                    "last_updated": _shared.get("last_updated"),
                    "category": cat,
                }
            self._json_response(result)

        elif parsed.path == "/api/channels":
            self._json_response(load_channels())

        elif parsed.path == "/api/refresh":
            threading.Thread(target=refresh_cache, daemon=True).start()
            self._json_response({"status": "refreshing"})

        elif parsed.path == "/" or parsed.path == "":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/channels/my":
            body = self._read_body()
            channels = load_channels()
            raw = body.get("channel", "").strip()
            if raw:
                cid = channel_id_from_input(raw)
                channels["my_channel"] = {"id": cid, "name": body.get("name", "")}
            else:
                channels["my_channel"] = None
            save_channels(channels)
            self._json_response({"ok": True, "channels": channels})
            threading.Thread(target=refresh_cache, daemon=True).start()

        elif self.path == "/api/channels/competitor":
            body = self._read_body()
            channels = load_channels()
            raw = body.get("channel", "").strip()
            if raw:
                cid = channel_id_from_input(raw)
                # 중복 체크
                existing = {c["id"] for c in channels["competitors"]}
                if cid not in existing:
                    channels["competitors"].append({
                        "id": cid,
                        "name": body.get("name", ""),
                    })
                    save_channels(channels)
            self._json_response({"ok": True, "channels": channels})
            threading.Thread(target=refresh_cache, daemon=True).start()

        elif self.path == "/api/channels/competitor/delete":
            body = self._read_body()
            channels = load_channels()
            cid = body.get("id", "")
            channels["competitors"] = [c for c in channels["competitors"] if c["id"] != cid]
            save_channels(channels)
            self._json_response({"ok": True, "channels": channels})

        elif self.path == "/api/category":
            body = self._read_body()
            channels = load_channels()
            channels["category"] = body.get("category", "economy")
            save_channels(channels)
            self._json_response({"ok": True, "category": channels["category"]})
            threading.Thread(target=refresh_cache, daemon=True).start()

        elif self.path == "/api/generate":
            body = self._read_body()
            keyword = body.get("keyword", "")
            category = body.get("category", "economy")
            articles = body.get("articles", [])
            result = {
                "script": generate_script(keyword, category, articles),
                "titles": generate_titles(keyword),
                "thumbnails": generate_thumbnails(keyword),
            }
            self._json_response(result)

        elif self.path == "/api/refresh":
            threading.Thread(target=refresh_cache, daemon=True).start()
            self._json_response({"status": "refreshing"})

        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


# ──────────────────────────────────────────────
#  메인
# ──────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir(BASE_DIR)

    # 채널 설정 초기화
    if not os.path.exists(CHANNELS_FILE):
        save_channels({"my_channel": None, "competitors": []})

    # 서버 먼저 시작 (데이터는 백그라운드에서 수집)
    # 클라우드 배포 시 PORT 환경변수 사용, 로컬은 자동 탐색
    env_port = os.environ.get("PORT")
    if env_port:
        port = int(env_port)
        server = HTTPServer(("0.0.0.0", port), Handler)
    else:
        port = 8585
        for p in [8585, 8686, 8787, 9090, 9191]:
            try:
                server = HTTPServer(("127.0.0.1", p), Handler)
                port = p
                break
            except OSError:
                continue
        else:
            print("[ERROR] 사용 가능한 포트를 찾을 수 없습니다.")
            input("Enter를 눌러 종료...")
        exit(1)

    url = f"http://localhost:{port}"
    print(f"\n{'='*45}")
    print(f"  경제 뉴스 트래커 실행 중")
    print(f"  {url}")
    print(f"  이 창을 닫으면 종료됩니다.")
    print(f"{'='*45}\n")

    # 로컬에서만 브라우저 자동 열기
    if not env_port:
        import webbrowser
        webbrowser.open(url)

    # 데이터 수집 시작 (백그라운드)
    threading.Thread(target=refresh_cache, daemon=True).start()

    # 자동 갱신 스레드
    threading.Thread(target=auto_refresh, daemon=True).start()

    server.serve_forever()
