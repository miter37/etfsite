"""
fetch_dividend_monthly.py
-------------------------
특정 ETF(기본값: TIGER 미국배당다우존스 458730)의 최근 N년(기본값: 2년)간
연도-월별 분배금 지급액과 당시 종가 대비 실질 배당수익률(%)을 시계열로 정밀 계산합니다.

계산 방식:
    1. SEIBRO 결제원 원장에서 지급기준일(RGT_STD_DT), 실지급일, 주당분배금을 수집
    2. pykrx를 통해 기준일(또는 직전 영업일) 당시의 실제 확정 종가를 매칭
    3. 회차별 배당수익률(%) = (주당분배금 / 당시종가) * 100
    4. 연환산 배당수익률(%) = 당시배당수익률 * (12 if 월배당 else 4)
    5. 연도별 누적 분배금 및 실질 연간 배당수익률, 현재가 대비 누적 회수율 요약

사용법:
    C:\\Python313\\python.exe scripts/fetch_dividend_monthly.py --ticker 458730 --years 2
    C:\\Python313\\python.exe scripts/fetch_dividend_monthly.py --ticker 161510 --years 3
    C:\\Python313\\python.exe scripts/fetch_dividend_monthly.py --ticker 498400 --years 2
"""

import sys
import os
import argparse
import datetime
import json
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from pykrx import stock

sys.stdout.reconfigure(encoding='utf-8')

SEIBRO_URL = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

def isin_of(ticker: str) -> str:
    """Luhn 알고리즘으로 단축 티커 -> 공식 풀 ISIN 자동 계산"""
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

def get_seibro_history(isin: str, start_dt: str, end_dt: str):
    """SEIBRO 결제원 원장에서 특정 기간 분배금 지급 내역 조회"""
    xml_body = f"""<reqParam action="exerInfoDtramtPayProgPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">
    <START_PAGE value="1"/>
    <END_PAGE value="100"/>
    <isin value="{isin}"/>
    <fromRGT_STD_DT value="{start_dt}"/>
    <toRGT_STD_DT value="{end_dt}"/>
</reqParam>"""
    try:
        res = requests.post(SEIBRO_URL, data=xml_body.encode('utf-8'), headers=HEADERS, timeout=15)
        root = ET.fromstring(res.text)
        rows = []
        for el in root.iter():
            if el.tag.endswith('result'):
                data = {child.tag: child.attrib.get('value', child.text) for child in el}
                if data:
                    rows.append(data)
        return rows
    except Exception as e:
        print(f"[오류] SEIBRO 분배금 조회 실패: {e}")
        return []

def get_etf_name(ticker: str) -> str:
    """etf_list_kr.json에서 종목명 조회"""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root_dir, "outputs")
    list_path = os.path.join(out_dir, "etf_list_kr.json")
    if not os.path.exists(list_path):
        list_path = os.path.join(root_dir, "etf_list_kr.json")
    if os.path.exists(list_path):
        try:
            with open(list_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if item.get("티커") == ticker:
                        return item.get("ETF명", ticker)
        except:
            pass
    return ticker

def run():
    parser = argparse.ArgumentParser(description="ETF 월별 분배금 및 당시 주가 대비 실질 배당수익률 분석기")
    parser.add_argument("--ticker", default="458730", help="ETF 단축 티커 (기본: 458730 TIGER 미국배당다우존스)")
    parser.add_argument("--years", type=int, default=2, help="조회 기간 (년 단위, 기본 2년)")
    parser.add_argument("--start-date", default=None, help="직접 시작일 지정 (YYYYMMDD)")
    parser.add_argument("--end-date", default=None, help="직접 종료일 지정 (YYYYMMDD)")
    args = parser.parse_args()

    today = datetime.date.today()
    if args.end_date:
        end_d = datetime.datetime.strptime(args.end_date, "%Y%m%d").date()
    else:
        end_d = today

    if args.start_date:
        start_d = datetime.datetime.strptime(args.start_date, "%Y%m%d").date()
    else:
        start_d = end_d - datetime.timedelta(days=int(args.years * 365.25))

    start_str = start_d.strftime("%Y%m%d")
    end_str = end_d.strftime("%Y%m%d")
    ticker = args.ticker.strip()
    isin = isin_of(ticker)
    etf_name = get_etf_name(ticker)

    print(f"=== [{ticker}] {etf_name} 월별 분배금 & 실질 배당수익률 분석 ===")
    print(f"  - 분석 기간: {start_d.strftime('%Y-%m-%d')} ~ {end_d.strftime('%Y-%m-%d')} (약 {args.years}년)")
    print(f"  - 공식 ISIN: {isin}")

    print("\n[1/3] SEIBRO 결제원 공식 분배금 내역 수집 중...")
    div_rows = get_seibro_history(isin, start_str, end_str)
    print(f"  - 기간 내 총 {len(div_rows)}회 분배금 지급 기록 확보")

    if not div_rows:
        print("[안내] 해당 기간에 지급된 분배금 내역이 없습니다.")
        return

    print("\n[2/3] pykrx 일별 확정 종가 시계열 수집 중...")
    # 시세 여유있게 전후 10일 추가
    price_start_str = (start_d - datetime.timedelta(days=15)).strftime("%Y%m%d")
    price_end_str = end_str
    df_price = stock.get_market_ohlcv(price_start_str, price_end_str, ticker)
    if df_price.empty:
        print("[경고] pykrx 일별 시세를 가져올 수 없습니다. 네이버 금융 백엔드 확인 필요.")
    else:
        df_price.index = pd.to_datetime(df_price.index).strftime("%Y%m%d")

    current_price_krw = float(df_price['종가'].iloc[-1]) if not df_price.empty else 0.0

    print("\n[3/3] 기준일 당시 종가와 매칭하여 실질 배당수익률 계산 중...")
    records = []
    for r in div_rows:
        std_dt = str(r.get("RGT_STD_DT", "")).strip()
        pay_dt = str(r.get("TH1_PAY_TERM_BEGIN_DT", "")).strip()
        div_krw = float(r.get("ESTM_STDPRC", 0) or 0)
        seibro_bunbe_pct = float(r.get("BUNBE", 0) or 0)
        tax_std_krw = float(r.get("TAXSTD", 0) or 0)

        # 기준일 당일 또는 직전 거래일의 종가 매칭
        price_at_that_time_krw = 0.0
        match_date = ""
        if not df_price.empty:
            sub = df_price[df_price.index <= std_dt]
            if not sub.empty:
                price_at_that_time_krw = float(sub.iloc[-1]['종가'])
                match_date = sub.index[-1]

        # 실질 배당수익률 계산
        if price_at_that_time_krw > 0:
            calc_yield_pct = round((div_krw / price_at_that_time_krw * 100), 3)
            annualized_yield_pct = round(calc_yield_pct * 12, 2)
        else:
            calc_yield_pct = 0.0
            annualized_yield_pct = 0.0

        year_month = f"{std_dt[:4]}-{std_dt[4:6]}" if len(std_dt) >= 6 else std_dt

        records.append({
            '연도_월': year_month,
            '지급기준일': f"{std_dt[:4]}-{std_dt[4:6]}-{std_dt[6:]}" if len(std_dt) == 8 else std_dt,
            '실지급일': f"{pay_dt[:4]}-{pay_dt[4:6]}-{pay_dt[6:]}" if len(pay_dt) == 8 else pay_dt,
            '주당분배금_원': int(div_krw),
            '당시종가_원': int(price_at_that_time_krw),
            '당시배당수익률_pct': calc_yield_pct,
            '연환산수익률_pct': annualized_yield_pct,
            'SEIBRO분배율_pct': seibro_bunbe_pct,
            '과표기준가_원': tax_std_krw,
            '종가매칭일': f"{match_date[:4]}-{match_date[4:6]}-{match_date[6:]}" if len(match_date) == 8 else match_date
        })

    # 기준일 오름차순 정렬 (과거 -> 최신)
    records.sort(key=lambda x: x['지급기준일'])
    df_monthly = pd.DataFrame(records)

    # 집계 및 요약 통계 계산
    total_payout_count = len(df_monthly)
    total_div_krw = int(df_monthly['주당분배금_원'].sum())
    avg_yield_pct = round(df_monthly['당시배당수익률_pct'].mean(), 3)
    avg_annualized_yield_pct = round(avg_yield_pct * 12, 2)
    recovery_rate_pct = round((total_div_krw / current_price_krw * 100), 2) if current_price_krw > 0 else 0.0

    # 연도별 분배금 요약
    df_monthly['연도'] = df_monthly['연도_월'].apply(lambda x: x.split('-')[0])
    yearly_summary = []
    for year, group in df_monthly.groupby('연도'):
        y_count = len(group)
        y_div_sum_krw = int(group['주당분배금_원'].sum())
        y_avg_price_krw = int(group['당시종가_원'].mean()) if not group.empty else 0
        y_yield_pct = round((y_div_sum_krw / y_avg_price_krw * 100), 2) if y_avg_price_krw > 0 else 0.0
        yearly_summary.append({
            '연도': year,
            '지급횟수': y_count,
            '연간_분배금합계_원': y_div_sum_krw,
            '연평균_주가_원': y_avg_price_krw,
            '연간_실질배당수익률_pct': y_yield_pct
        })
    df_yearly = pd.DataFrame(yearly_summary)

    # 출력 및 저장
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, f"{ticker}_dividend_monthly_{args.years}y.csv")
    json_path = os.path.join(out_dir, f"{ticker}_dividend_monthly_{args.years}y.json")

    # CSV 컬럼 정리
    save_cols = ['연도_월', '지급기준일', '실지급일', '주당분배금_원', '당시종가_원', '당시배당수익률_pct', '연환산수익률_pct', 'SEIBRO분배율_pct', '종가매칭일']
    df_monthly[save_cols].to_csv(csv_path, index=False, encoding="utf-8-sig")

    result_json = {
        'metadata': {
            'ticker': ticker,
            'name': etf_name,
            'isin': isin,
            'start_date': start_str,
            'end_date': end_str,
            'current_price_krw': current_price_krw
        },
        'summary': {
            'total_payout_count': total_payout_count,
            'total_div_krw': total_div_krw,
            'avg_monthly_yield_pct': avg_yield_pct,
            'avg_annualized_yield_pct': avg_annualized_yield_pct,
            'current_price_krw': current_price_krw,
            'recovery_rate_pct': recovery_rate_pct
        },
        'yearly_summary': yearly_summary,
        'monthly_history': records
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)

    print(f"\n[분석 완료]")
    print(f"  - 상세 시계열 CSV: {csv_path}")
    print(f"  - 종합 분석 JSON: {json_path}")

    print("\n" + "=" * 80)
    print(f"[{ticker}] {etf_name} 최근 {args.years}년 월별 분배금 & 당시 배당수익률 상세 내역")
    print("=" * 80)
    display_cols = ['연도_월', '지급기준일', '실지급일', '주당분배금_원', '당시종가_원', '당시배당수익률_pct', '연환산수익률_pct']
    print(df_monthly[display_cols].to_string(index=False))

    print("\n" + "-" * 80)
    print(f"[{ticker}] 연도별 분배금 및 실질 연간 배당수익률 요약")
    print("-" * 80)
    print(df_yearly.to_string(index=False))

    print("\n" + "=" * 80)
    print(f"총 분석 요약 (최근 {args.years}년 기준):")
    print(f"  • 총 분배금 지급 횟수: {total_payout_count}회")
    print(f"  • 누적 수령 분배금 합계: {total_div_krw:,}원")
    print(f"  • 현재 종가 기준: {int(current_price_krw):,}원")
    print(f"  • 현재가 대비 누적 분배금 회수율: {recovery_rate_pct:.2f}%")
    print(f"  • 1회(월) 평균 배당수익률: {avg_yield_pct:.2f}% (월배당 연환산: 약 {avg_annualized_yield_pct:.2f}%)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run()
