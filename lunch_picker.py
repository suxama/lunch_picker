#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종각역 반경 500m 점심 랜덤 추천기
- 다이닝코드에서 실시간으로 식당 데이터를 가져옵니다
"""

import json
import math
import random
import re
import sys
import urllib.parse
import urllib.request

# 종각역 좌표
JONGGAK_LAT = 37.5704
JONGGAK_LNG = 126.9831
RADIUS_M = 500

DININGCODE_URL = (
    "https://www.diningcode.com/list.dc"
    "?query=%EC%A2%85%EA%B0%81%EC%97%AD+%EC%A0%90%EC%8B%AC"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def haversine_m(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 거리를 미터로 반환."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_restaurants():
    """다이닝코드에서 종각역 근처 식당 목록을 가져온다."""
    print("다이닝코드에서 식당 정보를 불러오는 중...", flush=True)

    req = urllib.request.Request(DININGCODE_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    # localStorage.setItem('listData', '...') 에서 JSON 추출
    m = re.search(r"localStorage\.setItem\('listData',\s*'(.+?)'\);", html, re.DOTALL)
    if not m:
        raise RuntimeError("다이닝코드 페이지에서 데이터를 찾을 수 없습니다.")

    raw = m.group(1)
    # JS 문자열 이스케이프 해제: \" → "
    unescaped = raw.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
    data = json.loads(unescaped)

    poi_list = data.get("poi_section", {}).get("list", [])

    restaurants = []
    for item in poi_list:
        lat = item.get("lat")
        lng = item.get("lng")

        # 좌표가 있으면 500m 필터 적용
        if lat and lng:
            dist = haversine_m(JONGGAK_LAT, JONGGAK_LNG, lat, lng)
            if dist > RADIUS_M:
                continue
        else:
            dist = None

        category = item.get("category", "")
        if any(kw in category for kw in ["카페", "커피", "디저트", "베이커리"]):
            continue

        name = (item.get("nm") or "").strip()
        branch = (item.get("branch") or "").strip()
        full_name = f"{name} {branch}".strip() if branch else name
        if not full_name:
            continue

        review_raw = item.get("display_review", {}) or {}
        restaurants.append({
            "name": full_name,
            "category": item.get("category", ""),
            "address": item.get("road_addr") or item.get("addr", ""),
            "phone": item.get("phone", ""),
            "user_score": item.get("user_score", ""),
            "score": item.get("score", ""),
            "review_cnt": item.get("review_cnt", 0),
            "open_status": item.get("open_status", ""),
            "distance": int(dist) if dist is not None else None,
            "url": f"https://www.diningcode.com/profile.php?rid={item.get('v_rid', '')}",
            "keywords": [k["term"] for k in item.get("keyword", []) if k.get("term")],
            "image": item.get("image", ""),
            "area": ", ".join(item.get("area", [])),
            "latest_review": {
                "user": review_raw.get("user_nm", ""),
                "text": re.sub(r"<.*?>", "", review_raw.get("review_cont", "")),
                "date": review_raw.get("review_reg_dt", ""),
            } if review_raw else None,
        })

    # 거리순 정렬 (거리 없는 경우 뒤로)
    restaurants.sort(key=lambda r: r["distance"] if r["distance"] is not None else 9999)
    return restaurants


def print_banner():
    print("=" * 54)
    print("  🍱  종각역 반경 500m 점심 랜덤 추천기")
    print("  📡  실시간 데이터: 다이닝코드")
    print("=" * 54)


def print_recommendation(r):
    score = f"{r['user_score']}★" if r["user_score"] else "-"
    dc_score = f"{r['score']}점" if r["score"] else "-"
    dist = f"{r['distance']}m" if r["distance"] is not None else "-"
    reviews = f"{r['review_cnt']}개" if r["review_cnt"] else "-"
    status = r["open_status"] or "-"
    keywords = "  ".join(r["keywords"][:4]) if r["keywords"] else ""

    print()
    print("┌──────────────────────────────────────────────────┐")
    print(f"│  🍽  {r['name']}")
    print("├──────────────────────────────────────────────────┤")
    if r["category"]:
        print(f"│  종류     : {r['category']}")
    if r.get("area"):
        print(f"│  지역     : {r['area']}")
    print(f"│  평점     : {score}  /  다이닝코드 {dc_score}  (리뷰 {reviews})")
    print(f"│  거리     : 종각역에서 {dist}")
    print(f"│  영업상태 : {status}")
    if r["address"]:
        print(f"│  주소     : {r['address']}")
    if r["phone"]:
        print(f"│  전화     : {r['phone']}")
    if keywords:
        print(f"│  키워드   : {keywords}")
    if r.get("latest_review") and r["latest_review"]["text"]:
        rev = r["latest_review"]
        snippet = rev["text"][:60].replace("\n", " ")
        print(f"│  최신리뷰 : {rev['user']} ({rev['date']}) — {snippet}…")
    if r.get("image"):
        print(f"│  사진     : {r['image']}")
    print(f"│  상세정보 : {r['url']}")
    print("└──────────────────────────────────────────────────┘")
    print()


def interactive_mode(restaurants):
    open_list = [r for r in restaurants if "영업 중" in r.get("open_status", "")]
    print(f"\n종각역 반경 {RADIUS_M}m 내 식당 {len(restaurants)}개 (현재 영업 중 {len(open_list)}개)\n")

    while True:
        print("옵션을 선택하세요:")
        print("  1. 랜덤 추천 (전체)")
        print("  2. 랜덤 추천 (현재 영업 중만)")
        print("  3. 평점 TOP 10 보기")
        print("  4. 전체 목록 보기")
        print("  0. 종료")
        print()

        choice = input("선택 (0-4): ").strip()

        if choice == "0":
            print("\n오늘도 맛있는 점심 드세요! 👋\n")
            break

        elif choice in ("1", "2"):
            pool = open_list if choice == "2" else restaurants
            if not pool:
                print("⚠️  해당 조건의 식당이 없습니다.\n")
                continue
            pick = random.choice(pool)
            print_recommendation(pick)
            again = input("다시 뽑을까요? (y/n): ").strip().lower()
            if again != "y":
                print("\n오늘도 맛있는 점심 드세요! 👋\n")
                break
            print()

        elif choice == "3":
            top = sorted(
                [r for r in restaurants if r["user_score"]],
                key=lambda x: float(x["user_score"]),
                reverse=True,
            )[:10]
            print(f"\n[평점 TOP {len(top)}]")
            for i, r in enumerate(top, 1):
                dist = f"{r['distance']}m" if r["distance"] is not None else "  -  "
                status = "🟢" if "영업 중" in r.get("open_status", "") else "🔴"
                print(f"  {i:2}. {status} [{r['user_score']}★] {r['name']:<22} {r['category'][:12]:<12} ({dist})")
            print()

        elif choice == "4":
            print(f"\n{'#':>3}  {'영업':2}  {'평점':6}  {'거리':6}  {'이름':<22}  카테고리")
            print("-" * 65)
            for i, r in enumerate(restaurants, 1):
                score = f"{r['user_score']}★" if r["user_score"] else "  -  "
                dist = f"{r['distance']}m" if r["distance"] is not None else "  - "
                status = "🟢" if "영업 중" in r.get("open_status", "") else "🔴"
                print(f"  {i:3}. {status}  {score:<5}  {dist:<6}  {r['name']:<22}  {r['category']}")
            print()

        else:
            print("⚠️  올바른 번호를 입력해 주세요.\n")


def update_html(restaurants):
    """lunch_picker.html의 데이터와 타임스탬프를 최신으로 갱신."""
    import os
    from datetime import datetime

    base = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base, "index.html")
    if not os.path.exists(html_path):
        html_path = os.path.join(base, "lunch_picker.html")
    if not os.path.exists(html_path):
        print(f"⚠️  index.html / lunch_picker.html 파일을 찾을 수 없습니다.")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # const ALL = [...]; 교체
    new_data = "const ALL = " + json.dumps(restaurants, ensure_ascii=False) + ";"
    html = re.sub(r"const ALL = \[.*?\];", lambda _: new_data, html, flags=re.DOTALL)

    # 타임스탬프 교체 (동적 new Date() → 스크래핑 시각으로 고정)
    now = datetime.now()
    timestamp = f"{now.year}년 {now.month}월 {now.day}일 {now.hour}시 {now.minute:02d}분"
    html = re.sub(
        r"const now = new Date\(\);\s*document\.getElementById\('updated'\)\.textContent\s*=\s*`[^`]+`;",
        f"document.getElementById('updated').textContent = '데이터 기준: {timestamp}';",
        html,
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    open_cnt = sum(1 for r in restaurants if "영업 중" in r.get("open_status", ""))
    print(f"✅  {html_path} 업데이트 완료!")
    print(f"    식당 {len(restaurants)}개 / 현재 영업 중 {open_cnt}개 / 기준시각 {timestamp}")


def inspect_fields():
    """API 응답에 어떤 필드가 있는지 확인."""
    print("다이닝코드 API 필드 확인 중...", flush=True)
    req = urllib.request.Request(DININGCODE_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    m = re.search(r"localStorage\.setItem\('listData',\s*'(.+?)'\);", html, re.DOTALL)
    if not m:
        print("데이터를 찾을 수 없습니다.")
        return
    raw = m.group(1).replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
    data = json.loads(raw)
    items = data.get("poi_section", {}).get("list", [])
    if not items:
        print("식당 목록이 없습니다.")
        return
    sample = items[0]
    print(f"\n=== 샘플 식당: {sample.get('nm')} ===")
    print("전체 필드 목록:")
    for k, v in sample.items():
        print(f"  {k!r}: {v!r}")


def main():
    if "--inspect" in sys.argv:
        inspect_fields()
        return

    if "--update-html" in sys.argv:
        try:
            restaurants = fetch_restaurants()
        except Exception as e:
            print(f"\n⚠️  데이터를 불러오지 못했습니다: {e}")
            sys.exit(1)
        update_html(restaurants)
        return

    print_banner()
    try:
        restaurants = fetch_restaurants()
    except Exception as e:
        print(f"\n⚠️  데이터를 불러오지 못했습니다: {e}")
        sys.exit(1)

    if not restaurants:
        print(f"\n⚠️  종각역 반경 {RADIUS_M}m 내 식당을 찾을 수 없습니다.")
        sys.exit(1)

    interactive_mode(restaurants)


if __name__ == "__main__":
    main()
