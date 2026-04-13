"""경제 뉴스 트래커 — 핫한 경제 뉴스를 실시간으로 모아 보여주는 대시보드."""

import threading
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

from config import REFRESH_INTERVAL_MINUTES
from fetchers import (
    fetch_all_feeds,
    fetch_google_trends,
    analyze_hot_topics,
    check_youtube_competition,
    KST,
)

app = Flask(__name__)

# ──────────────────────────────────────────────
#  글로벌 데이터 저장소
# ──────────────────────────────────────────────

_data = {
    "articles": [],
    "hot_topics": [],
    "google_trends": [],
    "last_updated": None,
    "is_loading": False,
}
_lock = threading.Lock()


def refresh_data():
    """뉴스 데이터를 갱신한다."""
    with _lock:
        if _data["is_loading"]:
            return
        _data["is_loading"] = True

    try:
        print(f"\n[{datetime.now(KST).strftime('%H:%M:%S')}] 뉴스 수집 시작...")

        # 1) RSS 뉴스 수집
        articles = fetch_all_feeds()
        print(f"  총 {len(articles)}건 수집 완료")

        # 2) 핫 토픽 분석
        hot_topics = analyze_hot_topics(articles, hours=24)
        print(f"  핫 토픽 {len(hot_topics)}개 발견")

        # 3) 상위 핫 토픽 유튜브 경쟁도 체크
        for topic in hot_topics[:15]:
            topic.youtube_competition = check_youtube_competition(topic.keyword)

        # 4) Google Trends
        google_trends = fetch_google_trends()
        print(f"  구글 트렌드 {len(google_trends)}개")

        with _lock:
            _data["articles"] = articles
            _data["hot_topics"] = hot_topics
            _data["google_trends"] = google_trends
            _data["last_updated"] = datetime.now(KST)

        print(f"[{datetime.now(KST).strftime('%H:%M:%S')}] 갱신 완료!\n")

    except Exception as e:
        print(f"[ERROR] 갱신 실패: {e}")
    finally:
        with _lock:
            _data["is_loading"] = False


# ──────────────────────────────────────────────
#  라우트
# ──────────────────────────────────────────────

@app.route("/")
def index():
    with _lock:
        return render_template(
            "index.html",
            hot_topics=_data["hot_topics"][:20],
            google_trends=_data["google_trends"][:20],
            articles=_data["articles"][:50],
            last_updated=_data["last_updated"],
            is_loading=_data["is_loading"],
        )


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """수동 갱신 트리거."""
    threading.Thread(target=refresh_data, daemon=True).start()
    return jsonify({"status": "refreshing"})


@app.route("/api/data")
def api_data():
    """현재 데이터를 JSON으로 반환."""
    with _lock:
        topics = []
        for t in _data["hot_topics"][:20]:
            topics.append({
                "keyword": t.keyword,
                "score": t.score,
                "urgency": t.urgency,
                "age_hours": round(t.age_hours, 1),
                "youtube_competition": t.youtube_competition,
                "article_count": len(t.articles),
                "sources": list(set(a.source for a in t.articles)),
            })

        return jsonify({
            "hot_topics": topics,
            "google_trends": _data["google_trends"][:20],
            "article_count": len(_data["articles"]),
            "last_updated": _data["last_updated"].isoformat() if _data["last_updated"] else None,
        })


@app.route("/api/competition/<keyword>")
def api_competition(keyword):
    """특정 키워드의 유튜브 경쟁도를 체크한다."""
    count = check_youtube_competition(keyword)
    return jsonify({"keyword": keyword, "youtube_videos": count})


# ──────────────────────────────────────────────
#  스케줄러 & 실행
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # 첫 실행 시 데이터 수집
    refresh_data()

    # 주기적 갱신
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_data, "interval", minutes=REFRESH_INTERVAL_MINUTES)
    scheduler.start()

    print(f"\n{'='*50}")
    print(f"  경제 뉴스 트래커 실행 중")
    print(f"  http://localhost:5000")
    print(f"  갱신 주기: {REFRESH_INTERVAL_MINUTES}분")
    print(f"{'='*50}\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
