"""
fetch_ace_live.py
-----------------
한국투자신탁운용 ACE ETF 전용 실시간 API(papi.aceetf.co.kr)를 통해
장중/확정 순자산총액(AUM, 원 단위), 종목코드(6자리)가 포함된 실시간 PDF 편입종목,
그리고 최근 분배금 내역을 차단 위험 없이 즉시 수집합니다.

사용법:
    C:\\Python313\\python.exe scripts/fetch_ace_live.py --ticker 469150
    C:\\Python313\\python.exe scripts/fetch_ace_live.py --all
"""

import sys
import os
import argparse
import datetime
import json
import requests
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://papi.aceetf.co.kr/api/funds"

def get_all_ace_funds():
    """ACE ETF 전종목 마스터 목록 및 기본 시세/AUM 수집"""
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(BASE_URL, headers=headers)
    if res.status_code != 200:
        raise RuntimeError(f"ACE API 요청 실패: HTTP {res.status_code}")
    data = res.json()
    funds = data.get('data', [])
    records = []
    for f in funds:
        badge = f.get('badge', {}) or {}
        ticker = badge.get('stockCode') or ''
        fund_cd = f.get('fundCd', '')
        fund_nm = f.get('fundNm', '')
        aum_krw = int(f.get('nastAmt') or 0)
        nav_krw = float(f.get('stpr') or 0)
        close_krw = float(f.get('clpr') or 0)
        std_dt = str(f.get('stdDt', ''))
        records.append({
            '티커': ticker,
            '펀드코드': fund_cd,
            'ETF명': fund_nm,
            '기준일자': f"{std_dt[:4]}-{std_dt[4:6]}-{std_dt[6:]}" if len(std_dt) == 8 else std_dt,
            '현재가_원': close_krw,
            'NAV_원': nav_krw,
            '순자산총액_원': aum_krw,
            '순자산총액_억원': round(aum_krw / 1e8, 2),
            '자산분류': f.get('fundTypeNm', ''),
            'ISIN': f.get('stockCd', '')
        })
    return records

def get_fund_pdf(fund_cd):
    """특정 펀드의 실시간 PDF 편입종목 및 비중 조회 (6자리 종목코드 포함)"""
    url = f"{BASE_URL}/{fund_cd}/pdf?size=100"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        return []
    data = res.json()
    pdf_list = data.get('pdfList', [])
    rows = []
    for item in pdf_list:
        val_am_krw = int(item.get('val_AM') or 0)
        rows.append({
            '순위': item.get('rank'),
            '종목코드': item.get('jm_KSC_CD', ''),
            '종목명': item.get('sec_NM', ''),
            '비중_pct': float(item.get('wg') or 0),
            'CU당수량': float(item.get('cu_ITEM_CNT') or 0),
            'CU평가금액_원': val_am_krw,
            '기준일자': item.get('std_DT', '')
        })
    return rows

def get_fund_dividends(fund_cd):
    """특정 펀드의 최근 분배금 지급 내역 조회"""
    url = f"{BASE_URL}/{fund_cd}/dividend?size=100"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        return []
    data = res.json()
    div_list = data.get('dividendList', [])
    rows = []
    for d in div_list:
        rows.append({
            '지급기준일': d.get('payStdDate', ''),
            '지급일': d.get('payDate', ''),
            '주당분배금_원': float(d.get('dividendAmount') or 0),
            '분배율_pct': float(d.get('dividendRate') or 0)
        })
    return rows

def run():
    parser = argparse.ArgumentParser(description="ACE ETF 실시간 Live AUM & Holdings 수집기")
    parser.add_argument("--ticker", default="469150", help="ACE ETF 단축 티커 (기본값: 469150 ACE AI반도체TOP3+)")
    parser.add_argument("--all", action="store_true", help="전체 ACE ETF 마스터 요약 저장")
    args = parser.parse_args()

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(out_dir, exist_ok=True)

    print("=== [ACE ETF 실시간 수집기] ===")
    funds = get_all_ace_funds()
    print(f"  - ACE ETF 상장 펀드 총 {len(funds)}개 확인")

    if args.all:
        df_all = pd.DataFrame(funds)
        out_csv = os.path.join(out_dir, "ace_etf_all_live.csv")
        df_all.to_csv(out_csv, index=False, encoding="utf-8-sig")
        print(f"  - 전체 ACE ETF 목록 저장 완료: {out_csv}")
        return

    match = [f for f in funds if f['티커'] == args.ticker or f['펀드코드'] == args.ticker]
    if not match:
        print(f"  [오류] 티커/펀드코드 '{args.ticker}'를 찾을 수 없습니다.")
        return

    target = match[0]
    fund_cd = target['펀드코드']
    print(f"\n[대상 ETF] {target['ETF명']} (티커: {target['티커']}, 내부코드: {fund_cd})")
    print(f"  - 기준일자: {target['기준일자']}")
    print(f"  - 현재가: {target['현재가_원']:,}원 | NAV: {target['NAV_원']:,}원")
    print(f"  - 순자산총액(AUM): {target['순자산총액_원']:,}원 ({target['순자산총액_억원']:,}억원)")

    print("\n[PDF 편입종목 수집 중...]")
    pdf_rows = get_fund_pdf(fund_cd)
    print(f"  - 편입 종목 수: 총 {len(pdf_rows)}개 종목 (공식 6자리 주식코드 매핑 완료)")

    div_rows = get_fund_dividends(fund_cd)
    print(f"  - 최근 분배금 지급 기록: {len(div_rows)}회")

    # 저장
    df_pdf = pd.DataFrame(pdf_rows)
    pdf_csv_path = os.path.join(out_dir, f"ace_{target['티커']}_live_holdings.csv")
    df_pdf.to_csv(pdf_csv_path, index=False, encoding="utf-8-sig")

    summary_data = {
        "metadata": target,
        "holdings_count": len(pdf_rows),
        "holdings": pdf_rows,
        "dividends": div_rows
    }
    json_path = os.path.join(out_dir, f"ace_{target['티커']}_live_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print("\n[저장 완료]")
    print(f"  - 편입종목(PDF) CSV: {pdf_csv_path}")
    print(f"  - 종합 요약 JSON: {json_path}")

    if not df_pdf.empty:
        print("\n상위 5개 편입종목 미리보기:")
        print(df_pdf[['순위', '종목코드', '종목명', '비중_pct', 'CU당수량', 'CU평가금액_원']].head(5).to_string(index=False))

if __name__ == "__main__":
    run()
