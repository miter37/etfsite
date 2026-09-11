"""
fetch_etf_price_history.py
--------------------------
특정 ETF(기본값: KODEX 200, 069500)의 최근 시세(시/고/저/종/거래량),
확정 NAV 및 괴리율, 상장좌수/설정환매 시계열, 당일 PDF 편입종목을 수집합니다.

사용법:
    d:\\Python312\\python.exe scripts/fetch_etf_price_history.py --ticker 069500 --days 90
"""

import sys
import os
import argparse
import datetime
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pykrx import stock

sys.stdout.reconfigure(encoding='utf-8')

def isin_of(ticker: str) -> str:
    """단축 티커(예: 069500)로부터 Luhn 알고리즘을 적용한 공식 풀 ISIN을 계산"""
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
    check_digit = str((10 - tot % 10) % 10)
    return b + check_digit

def get_krx_mobile_session():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://m.krx.co.kr/contents/03/0303/030305/JHPETP030305M01.jsp'
    }
    session = requests.Session()
    key = session.get('https://m.krx.co.kr/contents/COM/JHPETPCM_KEY.jspx', headers=headers).text.strip()
    return session, key, headers

def fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """pykrx의 네이버 백엔드를 통해 안정적으로 시고저종/거래량/등락률 수집"""
    df = stock.get_market_ohlcv(start_date, end_date, ticker)
    if df.empty:
        return df
    df = df.reset_index()
    df.columns = ['일자', '시가_원', '고가_원', '저가_원', '종가_원', '거래량_주', '등락률_pct']
    df['일자'] = pd.to_datetime(df['일자']).dt.strftime('%Y-%m-%d')
    return df

def fetch_nav_and_deviation(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """m.krx.co.kr 030305 모바일 그리드를 통해 일별 확정 NAV 및 괴리율 수집"""
    isin = isin_of(ticker)
    session, key, headers = get_krx_mobile_session()
    url = 'https://m.krx.co.kr/inc/lib/mobilegrid/mobilegrid.jsp'
    params = {
        'mkt': 'ETF',
        'se_key': key,
        'isu_cd': isin,
        'domforn': '00',
        'uly_gubun': '00',
        'gubun': '00',
        'fromdate': start_date,
        'todate': end_date,
        'bldPath': '/03/0303/030305/hpetp030305m01'
    }
    r = session.get(url, params=params, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    rows = []
    for tr in soup.find_all('tr'):
        cols = [td.text.strip() for td in tr.find_all(['td', 'th'])]
        if len(cols) >= 4:
            # ['2026/09/11', '▼109,500', '109,608.14', '-0.10']
            date_str = cols[0].replace('/', '-')
            nav_str = cols[2].replace(',', '')
            dev_str = cols[3].replace(',', '')
            try:
                rows.append({
                    '일자': date_str,
                    'NAV_원': float(nav_str),
                    '괴리율_pct': float(dev_str)
                })
            except ValueError:
                continue
    df = pd.DataFrame(rows)
    return df

def fetch_shares_and_flow(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """m.krx.co.kr 030301을 통해 일자별 설정/환매 및 총 상장좌수 수집"""
    isin = isin_of(ticker)
    session, key, headers = get_krx_mobile_session()
    url = 'https://m.krx.co.kr/inc/lib/mobilegrid/mobilegrid.jsp'
    params = {
        'mkt': 'ETF',
        'se_key': key,
        'isu_cd': isin,
        'domforn': '00',
        'uly_gubun': '00',
        'gubun': '00',
        'fromdate': start_date,
        'todate': end_date,
        'bldPath': '/03/0303/030301/hpetp030301m02'
    }
    r = session.get(url, params=params, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    rows = []
    for tr in soup.find_all('tr'):
        cols = [td.text.strip() for td in tr.find_all(['td', 'th'])]
        if len(cols) >= 5:
            # ['2026/09/11', '설정좌수', '환매좌수', '순증감좌수', '상장좌수']
            date_str = cols[0].replace('/', '-')
            try:
                rows.append({
                    '일자': date_str,
                    '설정좌수': int(cols[1].replace(',', '')),
                    '환매좌수': int(cols[2].replace(',', '')),
                    '상장좌수': int(cols[4].replace(',', ''))
                })
            except ValueError:
                continue
    return pd.DataFrame(rows)

def fetch_latest_holdings(ticker: str, date_str: str) -> pd.DataFrame:
    """m.krx.co.kr 030302를 통해 ETF의 당일 PDF 포트폴리오 편입비중 수집"""
    isin = isin_of(ticker)
    session, key, headers = get_krx_mobile_session()
    url = 'https://m.krx.co.kr/inc/lib/mobilegrid/mobilegrid.jsp'
    params = {
        'mkt': 'ETF',
        'se_key': key,
        'isu_cd': isin,
        'domforn': '00',
        'uly_gubun': '00',
        'gubun': '00',
        'date': date_str,
        'bldPath': '/03/0303/030302/hpetp030302m01'
    }
    r = session.get(url, params=params, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    rows = []
    for tr in soup.find_all('tr'):
        cols = [td.text.strip() for td in tr.find_all(['td', 'th'])]
        if len(cols) >= 5:
            # ['삼성전자', '6,924.00', '-', '1,796,778,000', '32.79']
            try:
                rows.append({
                    '종목명': cols[0],
                    'CU당수량': float(cols[1].replace(',', '')),
                    '평가금액_원': int(cols[3].replace(',', '')),
                    '비중_pct': float(cols[4].replace(',', ''))
                })
            except ValueError:
                continue
    return pd.DataFrame(rows)

def run():
    parser = argparse.ArgumentParser(description="ETF Price, NAV, and Metrics History Collector")
    parser.add_argument("--ticker", default="069500", help="ETF 6자리 티커 (예: 069500)")
    parser.add_argument("--days", type=int, default=90, help="과거 조회 일수 (기본 90일 = 약 3개월)")
    args = parser.parse_args()

    end_d = datetime.date.today()
    start_d = end_d - datetime.timedelta(days=args.days)
    start_str = start_d.strftime('%Y%m%d')
    end_str = end_d.strftime('%Y%m%d')

    print(f"=== [{args.ticker}] 최근 {args.days}일 데이터 수집 ({start_str} ~ {end_str}) ===")

    print("[1/4] 일별 시고저종/거래량 수집 중 (pykrx)...")
    df_ohlcv = fetch_ohlcv(args.ticker, start_str, end_str)
    print(f"  - 시세 데이터: {len(df_ohlcv)} 거래일 수집 완료")

    print("[2/4] 일별 확정 NAV 및 괴리율 수집 중 (m.krx)...")
    df_nav = fetch_nav_and_deviation(args.ticker, start_str, end_str)
    print(f"  - NAV 데이터: {len(df_nav)} 거래일 수집 완료")

    print("[3/4] 일별 상장좌수 및 설정/환매 수집 중 (m.krx)...")
    df_flow = fetch_shares_and_flow(args.ticker, start_str, end_str)
    print(f"  - 상장좌수 데이터: {len(df_flow)} 거래일 수집 완료")

    # 병합
    df_merged = df_ohlcv
    if not df_nav.empty:
        df_merged = pd.merge(df_merged, df_nav, on='일자', how='left')
    if not df_flow.empty:
        df_merged = pd.merge(df_merged, df_flow, on='일자', how='left')

    # 단위 규율 준수 및 순자산가치(AUM) 역산
    if '종가_원' in df_merged.columns and '상장좌수' in df_merged.columns:
        df_merged['시가총액_원'] = (df_merged['종가_원'] * df_merged['상장좌수']).fillna(0).astype('int64')
        df_merged['시가총액_억원'] = (df_merged['시가총액_원'] / 1e8).round(2)
    if 'NAV_원' in df_merged.columns and '상장좌수' in df_merged.columns:
        df_merged['순자산가치_AUM_원'] = (df_merged['NAV_원'] * df_merged['상장좌수']).fillna(0).round().astype('int64')
        df_merged['순자산가치_AUM_억원'] = (df_merged['순자산가치_AUM_원'] / 1e8).round(2)

    print("[4/4] 당일 포트폴리오(PDF) 상위 구성종목 수집 중...")
    df_pdf = fetch_latest_holdings(args.ticker, end_str)
    print(f"  - PDF 편입종목: 총 {len(df_pdf)} 종목 수집 완료")

    # 저장
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    days_tag = "1y" if args.days in (365, 366) else ("2y" if args.days in (730, 731) else ("3m" if args.days in (90, 91) else f"{args.days}d"))
    out_csv = os.path.join(out_dir, f"{args.ticker}_price_history_{days_tag}.csv")
    out_json = os.path.join(out_dir, f"{args.ticker}_price_history_{days_tag}.json")
    out_pdf_csv = os.path.join(out_dir, f"{args.ticker}_latest_pdf.csv")

    df_merged.to_csv(out_csv, index=False, encoding='utf-8-sig')
    df_merged.to_json(out_json, orient='records', force_ascii=False, indent=2)
    if not df_pdf.empty:
        df_pdf.to_csv(out_pdf_csv, index=False, encoding='utf-8-sig')

    print(f"\n[저장 완료]")
    print(f"  - 일별 시세/NAV 통합 이력: {out_csv}")
    print(f"  - 당일 최신 PDF 보유종목: {out_pdf_csv}")
    print("\n최근 5거래일 데이터 요약:")
    summary_cols = [c for c in ['일자', '종가_원', 'NAV_원', '괴리율_pct', '거래량_주', '상장좌수', '시가총액_억원'] if c in df_merged.columns]
    print(df_merged[summary_cols].tail(5).to_string(index=False))

if __name__ == "__main__":
    run()
