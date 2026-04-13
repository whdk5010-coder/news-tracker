"""뉴스 트래커 설정"""

# 뉴스 소스 RSS 피드
NEWS_FEEDS = {
    # Google News 한국 주요 뉴스
    "google_top_kr": {
        "name": "구글 주요",
        "url": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
        "category": "general",
    },
    # Google News 한국 비즈니스/경제
    "google_business_kr": {
        "name": "구글 경제",
        "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko",
        "category": "economy",
    },
    # Google News 경제 검색
    "google_economy_search": {
        "name": "구글 경제검색",
        "url": "https://news.google.com/rss/search?q=%EA%B2%BD%EC%A0%9C&hl=ko&gl=KR&ceid=KR:ko",
        "category": "economy",
    },
    # Google News 주식/증시 검색
    "google_stock_search": {
        "name": "구글 증시",
        "url": "https://news.google.com/rss/search?q=%EC%A3%BC%EC%8B%9D+%EC%A6%9D%EC%8B%9C&hl=ko&gl=KR&ceid=KR:ko",
        "category": "stock",
    },
    # 한국경제
    "hankyung": {
        "name": "한국경제",
        "url": "https://www.hankyung.com/feed/all-news",
        "category": "economy",
    },
    # 매일경제
    "mk": {
        "name": "매일경제",
        "url": "https://www.mk.co.kr/rss/30000001/",
        "category": "economy",
    },
    # 연합뉴스TV 경제
    "yonhap_economy": {
        "name": "연합뉴스",
        "url": "https://www.yonhapnewstv.co.kr/category/news/economy/feed/",
        "category": "economy",
    },
}

# 키워드 추출 시 제외할 불용어
STOPWORDS = {
    "것", "수", "등", "이", "그", "저", "및", "또", "더", "위", "중",
    "대한", "통해", "위해", "있는", "하는", "되는", "없는", "같은",
    "오늘", "내일", "어제", "올해", "지난", "최근", "현재", "다시",
    "뉴스", "속보", "단독", "종합", "업데이트", "포토", "영상",
    "기자", "특파원", "앵커", "리포트", "인터뷰",
    "한국", "국내", "해외", "세계", "글로벌", "전세계",
    "정부", "대통령", "나라", "우리", "모두", "사람",
    "가능", "예상", "전망", "분석", "발표", "확인", "결정",
    "시장", "경제",  # 너무 일반적
    "만에", "이후", "가장", "처음", "결국", "때문", "바로",
}

# 핫 토픽 판정 기준 (N개 이상 소스에서 언급되면 HOT)
HOT_THRESHOLD = 3

# 뉴스 갱신 주기 (분)
REFRESH_INTERVAL_MINUTES = 30

# 최대 보관 뉴스 수
MAX_ARTICLES = 500
