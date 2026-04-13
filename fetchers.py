"""뉴스 수집 모듈 - RSS 피드 기반으로 경제 뉴스를 가져온다."""

import re
import sys
import time
import hashlib
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import feedparser
import requests
from bs4 import BeautifulSoup

from config import NEWS_FEEDS, STOPWORDS, HOT_THRESHOLD, MAX_ARTICLES

KST = timezone(timedelta(hours=9))


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: datetime
    category: str
    keywords: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return hashlib.md5(self.link.encode()).hexdigest()[:12]

    @property
    def age_hours(self) -> float:
        now = datetime.now(KST)
        pub = self.published if self.published.tzinfo else self.published.replace(tzinfo=KST)
        return (now - pub).total_seconds() / 3600


@dataclass
class HotTopic:
    keyword: str
    score: int  # 몇 개 소스에서 언급됐는지
    articles: list[Article]
    first_seen: datetime
    youtube_competition: int = 0  # 유튜브에 이미 올라온 영상 수

    @property
    def age_hours(self) -> float:
        now = datetime.now(KST)
        fs = self.first_seen if self.first_seen.tzinfo else self.first_seen.replace(tzinfo=KST)
        return (now - fs).total_seconds() / 3600

    @property
    def urgency(self) -> str:
        h = self.age_hours
        if h < 3:
            return "NOW"
        elif h < 6:
            return "HOT"
        elif h < 12:
            return "WARM"
        else:
            return "COOL"


# ──────────────────────────────────────────────
#  RSS 수집
# ──────────────────────────────────────────────

def _parse_date(entry) -> datetime:
    """feedparser 엔트리에서 날짜를 파싱한다."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return datetime(*t[:6], tzinfo=KST)
    return datetime.now(KST)


def _clean_html(text: str) -> str:
    """HTML 태그 제거."""
    if not text:
        return ""
    return BeautifulSoup(text, "lxml").get_text(strip=True)


def fetch_feed(feed_id: str, feed_config: dict) -> list[Article]:
    """단일 RSS 피드에서 기사를 수집한다."""
    articles = []
    try:
        resp = requests.get(
            feed_config["url"],
            timeout=15,
            headers={"User-Agent": "NewsTracker/1.0"},
        )
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            title = _clean_html(entry.get("title", ""))
            if not title:
                continue
            articles.append(Article(
                title=title,
                link=entry.get("link", ""),
                source=feed_config["name"],
                published=_parse_date(entry),
                category=feed_config["category"],
                keywords=extract_keywords(title),
            ))
    except Exception as e:
        print(f"[WARN] {feed_config['name']} 수집 실패: {e}")

    return articles


def fetch_all_feeds() -> list[Article]:
    """모든 RSS 피드에서 기사를 수집한다."""
    all_articles = []
    for feed_id, feed_config in NEWS_FEEDS.items():
        articles = fetch_feed(feed_id, feed_config)
        all_articles.extend(articles)
        print(f"  [{feed_config['name']}] {len(articles)}건 수집")

    # 중복 제거 (같은 URL)
    seen = set()
    unique = []
    for a in all_articles:
        if a.id not in seen:
            seen.add(a.id)
            unique.append(a)

    # 최신순 정렬
    unique.sort(key=lambda a: a.published, reverse=True)
    return unique[:MAX_ARTICLES]


# ──────────────────────────────────────────────
#  키워드 추출 (간단한 한국어 명사 추출)
# ──────────────────────────────────────────────

# 경제 관련 핵심 키워드 패턴
ECON_PATTERNS = [
    # 시장/지수
    r"코스피|코스닥|나스닥|S&P|다우|니케이|항셍",
    # 환율/금리
    r"환율|금리|기준금리|인상|인하|동결",
    # 원자재
    r"유가|금값|원유|WTI|브렌트|구리|천연가스",
    # 부동산
    r"부동산|아파트|전세|월세|분양|재건축|재개발",
    # 기관/정책
    r"한은|연준|Fed|ECB|IMF|OECD|기재부|금감원",
    # 산업
    r"반도체|AI|배터리|2차전지|방산|바이오|자동차",
    # 기업
    r"삼성|SK|현대|LG|네이버|카카오|테슬라|엔비디아|애플",
    # 국가/지정학
    r"미국|중국|일본|러시아|이란|우크라이나|북한|대만|인도",
    # 투자
    r"ETF|주식|채권|펀드|연금|ISA|IRA",
    # 경제 현상
    r"인플레|디플레|스태그플레이션|관세|무역전쟁|제재|수출|수입",
]

ECON_RE = re.compile("|".join(ECON_PATTERNS))

# 2글자 이상 한글 단어 추출 (조사 제거 시도)
KOREAN_WORD_RE = re.compile(r"[가-힣]{2,}")
# 흔한 조사/어미 패턴 제거
SUFFIX_RE = re.compile(r"(에서|으로|에게|까지|부터|에서는|으로는|이다|하는|되는|했다|됐다|한다|된다)$")


def extract_keywords(title: str) -> list[str]:
    """제목에서 경제 관련 키워드를 추출한다."""
    keywords = set()

    # 1) 경제 패턴 매칭
    for match in ECON_RE.finditer(title):
        keywords.add(match.group())

    # 2) 숫자+단위 패턴 (예: 286%, 45조, 1500원)
    for match in re.finditer(r"\d+[%조억만원달러엔위안]", title):
        keywords.add(match.group())

    # 3) 한글 단어 추출 (불용어 제외)
    for match in KOREAN_WORD_RE.finditer(title):
        word = match.group()
        word = SUFFIX_RE.sub("", word)
        if len(word) >= 2 and word not in STOPWORDS:
            keywords.add(word)

    return list(keywords)


# ──────────────────────────────────────────────
#  핫 토픽 분석
# ──────────────────────────────────────────────

def analyze_hot_topics(articles: list[Article], hours: int = 24) -> list[HotTopic]:
    """최근 N시간 이내 기사들에서 핫 토픽을 추출한다."""
    now = datetime.now(KST)
    cutoff = now - timedelta(hours=hours)

    recent = [a for a in articles if a.published.replace(tzinfo=KST) > cutoff]

    # 키워드별 기사 그룹핑
    keyword_articles: dict[str, list[Article]] = {}
    for article in recent:
        for kw in article.keywords:
            if len(kw) < 2:
                continue
            keyword_articles.setdefault(kw, []).append(article)

    # 소스 다양성 기준으로 점수 계산
    topics = []
    for kw, arts in keyword_articles.items():
        sources = set(a.source for a in arts)
        score = len(sources)  # 몇 개 소스에서 언급됐는지
        if score >= 2:  # 최소 2개 소스에서 언급
            earliest = min(a.published for a in arts)
            topics.append(HotTopic(
                keyword=kw,
                score=score,
                articles=arts,
                first_seen=earliest,
            ))

    # 점수 높은 순 → 최신 순
    topics.sort(key=lambda t: (-t.score, t.first_seen), reverse=False)
    return topics


# ──────────────────────────────────────────────
#  유튜브 경쟁도 체크
# ──────────────────────────────────────────────

def check_youtube_competition(keyword: str) -> int:
    """유튜브에서 해당 키워드로 검색했을 때 최근 영상 수를 추정한다."""
    try:
        url = f"https://www.youtube.com/results?search_query={requests.utils.quote(keyword)}&sp=CAI%253D"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9",
        })
        # 대략적인 영상 수 추정 (videoId 개수)
        count = resp.text.count('"videoId"')
        return count
    except Exception:
        return -1


# ──────────────────────────────────────────────
#  Google Trends 급상승 검색어
# ──────────────────────────────────────────────

def fetch_google_trends() -> list[dict]:
    """Google Trends 급상승 검색어(한국)를 가져온다."""
    trends = []
    try:
        url = "https://trends.google.co.kr/trending/rss?geo=KR"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "NewsTracker/1.0"})
        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            title = entry.get("title", "")
            traffic = entry.get("ht_approx_traffic", "")
            news_items = []

            # 관련 뉴스 추출
            if hasattr(entry, "ht_news_item_title"):
                news_items.append(entry.ht_news_item_title)

            trends.append({
                "keyword": title,
                "traffic": traffic,
                "news": news_items,
                "link": entry.get("link", ""),
            })
    except Exception as e:
        print(f"[WARN] Google Trends 수집 실패: {e}")

    return trends
