"""
fetch_dividend_history.py
-------------------------
한국예탁결제원 증권정보포털(SEIBRO)의 공식 결제 원장 서블릿 API를 통해
특정 ETF(티커/ISIN 입력 가능) 또는 대표 배당 ETF들의 전회차 분배금 지급 히스토리를 일괄 수집합니다.

사용법:
    C:\\Python313\\python.exe scripts/fetch_dividend_history.py --ticker 458730
    C:\\Python313\\python.exe scripts/fetch_dividend_history.py --ticker 161510
    C:\\Python313\\python.exe scripts/fetch_dividend_history.py   # 기본 대표 6종 실행
"""

import sys
import json
import os
import argparse
import requests
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

def isin_of(ticker: str) -> str:
    """단축 티커(예: 458730)로부터 Luhn 알고리즘을 적용한 공식 풀 ISIN을 계산"""
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

def get_seibro_history(isin):
    xml_body = f"""<reqParam action="exerInfoDtramtPayProgPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">
    <START_PAGE value="1"/>
    <END_PAGE value="100"/>
    <isin value="{isin}"/>
    <fromRGT_STD_DT value="20150101"/>
    <toRGT_STD_DT value="20261231"/>
</reqParam>"""
    res = requests.post(url, data=xml_body.encode('utf-8'), headers=headers)
    root = ET.fromstring(res.text)
    rows = []
    for el in root.iter():
        if el.tag.endswith('result'):
            data = {child.tag: child.attrib.get('value', child.text) for child in el}
            if data:
                rows.append(data)
    return rows

def run():
    parser = argparse.ArgumentParser(description="SEIBRO ETF 분배금 지급 히스토리 수집기")
    parser.add_argument("--ticker", default=None, help="조회할 ETF 단축 티커 (예: 458730)")
    parser.add_argument("--isin", default=None, help="조회할 ETF 풀 ISIN (예: KR7458730009)")
    args = parser.parse_args()

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    if args.ticker or args.isin:
        ticker = args.ticker or ''
        isin = args.isin if args.isin else isin_of(ticker)
        print(f"=== [단일 ETF 분배금 조회] 티커: {ticker} | ISIN: {isin} ===")
        rows = get_seibro_history(isin)
        history = []
        for r in rows:
            history.append({
                "기준일": r.get("RGT_STD_DT"),
                "실지급일": r.get("TH1_PAY_TERM_BEGIN_DT"),
                "주당분배금_원": float(r.get("ESTM_STDPRC", 0)) if r.get("ESTM_STDPRC") else 0,
                "분배율_pct": float(r.get("BUNBE", 0)) if r.get("BUNBE") else 0,
                "과표기준가_원": float(r.get("TAXSTD", 0)) if r.get("TAXSTD") else 0
            })
        result = {
            "ticker": ticker,
            "isin": isin,
            "total_count": len(history),
            "history": history
        }
        out_path = os.path.join(output_dir, f"{ticker or isin}_dividend_history.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  - 총 {len(history)}회 분배금 수집 완료 -> {out_path}")
        if history:
            print("\n최근 3회 분배금 내역:")
            for h in history[:3]:
                print(f"  기준일: {h['기준일']} | 지급일: {h['실지급일']} | 분배금: {h['주당분배금_원']:,.0f}원 | 분배율: {h['분배율_pct']}%")
        return

    # 기본 6선 벤치마크
    target_etfs = [
        {"category": "대표 배당주", "ticker": "161510", "isin": "KR7161510003", "name": "PLUS 고배당주", "issuer": "한화자산운용"},
        {"category": "대표 배당주", "ticker": "458730", "isin": "KR7458730009", "name": "TIGER 미국배당다우존스", "issuer": "미래에셋자산운용"},
        {"category": "대표 배당주", "ticker": "466940", "isin": "KR7466940004", "name": "TIGER 은행고배당플러스TOP10", "issuer": "미래에셋자산운용"},
        {"category": "대표 월지급식(인컴)", "ticker": "498400", "isin": "KR7498400001", "name": "KODEX 200타겟위클리커버드콜", "issuer": "삼성자산운용"},
        {"category": "대표 월지급식(인컴)", "ticker": "472150", "isin": "KR7472150002", "name": "TIGER 배당커버드콜액티브", "issuer": "미래에셋자산운용"},
        {"category": "대표 월지급식(인컴)", "ticker": "441640", "isin": "KR7441640000", "name": "KODEX 미국배당커버드콜액티브", "issuer": "삼성자산운용"}
    ]

    all_results = {}
    for target in target_etfs:
        isin = target['isin']
        name = target['name']
        print(f"[{target['category']}] {name} ({isin}) 분배금 내역 수집 중...")
        rows = get_seibro_history(isin)
        target_data = []
        for r in rows:
            target_data.append({
                "기준일": r.get("RGT_STD_DT"),
                "실지급일": r.get("TH1_PAY_TERM_BEGIN_DT"),
                "주당분배금_원": float(r.get("ESTM_STDPRC", 0)) if r.get("ESTM_STDPRC") else 0,
                "분배율_pct": float(r.get("BUNBE", 0)) if r.get("BUNBE") else 0,
                "과표기준가_원": float(r.get("TAXSTD", 0)) if r.get("TAXSTD") else 0
            })
        all_results[target['ticker']] = {
            "metadata": target,
            "history": target_data
        }

    out_path = os.path.join(output_dir, "selected_etfs_dividend_history.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root_dir, "selected_etfs_dividend_history.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"  - 완료: {out_path} 저장 성공!")

if __name__ == "__main__":
    run()
