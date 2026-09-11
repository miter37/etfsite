"""
fetch_dividend_screener.py
--------------------------
국내 상장된 주요 배당/인컴/커버드콜 ETF들을 자동 선별하여,
SEIBRO 결제원 원장 API를 통해 과거 1년치 분배금을 집계하고
연환산 시가 배당수익률(%), 배당주기(월배당 여부), 최근 지급 현황을 계산해 랭킹을 생성합니다.

사용법:
    C:\\Python313\\python.exe scripts/fetch_dividend_screener.py --top 30
"""

import sys
import os
import argparse
import datetime
import json
import time
import requests
import xml.etree.ElementTree as ET
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

SEIBRO_URL = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

def isin_of(ticker: str) -> str:
    b = 'KR7' + ticker + '00'
    s = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in b)
    tot = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
    return b + str((10 - tot % 10) % 10)

def get_seibro_history(isin):
    xml_body = f"""<reqParam action="exerInfoDtramtPayProgPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">
    <START_PAGE value="1"/>
    <END_PAGE value="50"/>
    <isin value="{isin}"/>
    <fromRGT_STD_DT value="20250101"/>
    <toRGT_STD_DT value="20261231"/>
</reqParam>"""
    try:
        res = requests.post(SEIBRO_URL, data=xml_body.encode('utf-8'), headers=HEADERS, timeout=10)
        root = ET.fromstring(res.text)
        rows = []
        for el in root.iter():
            if el.tag.endswith('result'):
                data = {child.tag: child.attrib.get('value', child.text) for child in el}
                if data:
                    rows.append(data)
        return rows
    except Exception as e:
        return []

def run():
    parser = argparse.ArgumentParser(description="배당/인컴 ETF 스크리너 및 랭킹 생성기")
    parser.add_argument("--top", type=int, default=25, help="분석 대상 배당 ETF 수 (시가총액 상위 N개, 기본 25)")
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root_dir, "outputs")
    list_path = os.path.join(out_dir, "etf_list_kr.json")
    if not os.path.exists(list_path):
        list_path = os.path.join(root_dir, "etf_list_kr.json")

    if not os.path.exists(list_path):
        print(f"[오류] {list_path} 가 존재하지 않습니다. fetch_etf_list.py를 먼저 실행하세요.")
        return

    with open(list_path, "r", encoding="utf-8") as f:
        all_etfs = json.load(f)

    # 배당 관련 키워드 필터링
    keywords = ["배당", "고배당", "커버드콜", "인컴", "월지급", "프리미엄", "다우존스", "리츠"]
    candidate_etfs = []
    for etf in all_etfs:
        name = etf.get('ETF명', '')
        idx = etf.get('기초지수명', '')
        if any(k in name or k in idx for k in keywords):
            # 레버리지/인버스 제외
            if "레버리지" not in name and "인버스" not in name:
                candidate_etfs.append(etf)

    # 시가총액 순 정렬 후 상위 선택
    candidate_etfs.sort(key=lambda x: x.get('시가총액_원', 0), reverse=True)
    selected = candidate_etfs[:args.top]
    print(f"=== [배당 ETF 스크리너] 시총 상위 {len(selected)}개 종목 분석 시작 ===")

    today = datetime.date.today()
    one_year_ago_str = (today - datetime.timedelta(days=365)).strftime('%Y%m%d')

    ranking_rows = []
    for idx, etf in enumerate(selected, 1):
        ticker = etf.get('티커', '')
        isin = etf.get('ISIN') or isin_of(ticker)
        name = etf.get('ETF명', '')
        close_krw = float(etf.get('현재가_원', 0))
        mktcap_eok = float(etf.get('시가총액_억원', 0))
        issuer = etf.get('운용사', '')

        print(f"[{idx}/{len(selected)}] {name} ({ticker}) 분배금 조회 중...")
        history = get_seibro_history(isin)

        # 1년 내 지급 분배금 집계
        div_1y_krw = 0.0
        payout_count_1y = 0
        recent_payout_krw = 0.0
        recent_payout_date = ""

        for r in history:
            std_dt = str(r.get("RGT_STD_DT", ""))
            amount = float(r.get("ESTM_STDPRC", 0) or 0)
            if not recent_payout_date and amount > 0:
                recent_payout_date = std_dt
                recent_payout_krw = amount

            if std_dt >= one_year_ago_str:
                div_1y_krw += amount
                if amount > 0:
                    payout_count_1y += 1

        # 배당 주기 판별
        if payout_count_1y >= 10:
            cycle = "월배당"
        elif payout_count_1y >= 3:
            cycle = "분기배당"
        elif payout_count_1y >= 1:
            cycle = "연배당/반기"
        else:
            cycle = "신규상장/무배당"

        # 시가 배당수익률 계산
        div_yield_pct = round((div_1y_krw / close_krw * 100), 2) if close_krw > 0 else 0.0

        ranking_rows.append({
            '티커': ticker,
            'ISIN': isin,
            'ETF명': name,
            '운용사': issuer,
            '현재가_원': close_krw,
            '시가총액_억원': mktcap_eok,
            '배당주기': cycle,
            '연간지급횟수': payout_count_1y,
            '최근1년_주당분배금_원': round(div_1y_krw),
            '배당수익률_pct': div_yield_pct,
            '최근분배금_원': recent_payout_krw,
            '최근지급기준일': f"{recent_payout_date[:4]}-{recent_payout_date[4:6]}-{recent_payout_date[6:]}" if len(recent_payout_date) == 8 else recent_payout_date
        })
        time.sleep(0.1)

    df_rank = pd.DataFrame(ranking_rows)
    df_rank = df_rank.sort_values(by='배당수익률_pct', ascending=False).reset_index(drop=True)

    csv_out = os.path.join(out_dir, "dividend_screener_ranking.csv")
    json_out = os.path.join(out_dir, "dividend_screener_ranking.json")

    df_rank.to_csv(csv_out, index=False, encoding="utf-8-sig")
    df_rank.to_json(json_out, orient="records", force_ascii=False, indent=2)

    print(f"\n[저장 완료]")
    print(f"  - 배당 랭킹 CSV: {csv_out}")
    print(f"  - 배당 랭킹 JSON: {json_out}")

    print("\n=== 배당수익률 TOP 10 요약 ===")
    show_cols = ['티커', 'ETF명', '현재가_원', '시가총액_억원', '배당주기', '최근1년_주당분배금_원', '배당수익률_pct']
    print(df_rank[show_cols].head(10).to_string(index=False))

if __name__ == "__main__":
    run()
