import os, shutil

root = r"D:\APPs\etfsite"

fetch_list_code = '''"""
fetch_etf_list.py
-----------------
한국거래소(KRX) 공인 백엔드를 통해 국내 상장된 전체 ETF(1,160+개)의
마스터 메타데이터와 당일 종가/시가총액/NAV를 일괄 수집하여 저장합니다.

사용법:
    D:\\H2\\hermes-agent\\venv\\Scripts\\python.exe scripts/fetch_etf_list.py
"""

import sys
import json
import os
import datetime
import pandas as pd
from pykrx.website.krx.etx import core

sys.stdout.reconfigure(encoding='utf-8')

def clean_num(val):
    if pd.isna(val) or val == '-' or val == '':
        return 0
    if isinstance(val, (int, float)):
        return val
    s = str(val).replace(',', '').strip()
    try:
        return float(s) if '.' in s else int(s)
    except:
        return 0

def run():
    print("[1/3] KRX 전체 ETF 기본 마스터 데이터 수집 중...")
    df_master = core.ETF_전종목기본종목().fetch()
    print(f"  - 마스터 수집 완료: {len(df_master)} 종목")

    today_str = datetime.date.today().strftime('%Y%m%d')
    print(f"[2/3] 당일 시세 및 시가총액 결합 중 (기준일: {today_str})...")
    df_market = core.전종목시세_ETF().fetch(today_str)
    print(f"  - 시세 수집 완료: {len(df_market)} 종목")

    merged = pd.merge(
        df_master,
        df_market[['ISU_SRT_CD', 'TDD_CLSPRC', 'CMPPREVDD_PRC', 'FLUC_RT', 'NAV', 'ACC_TRDVOL', 'ACC_TRDVAL', 'MKTCAP', 'INVSTASST_NETASST_TOTAMT']],
        on='ISU_SRT_CD',
        how='left'
    )

    records = []
    for _, r in merged.iterrows():
        mktcap_krw = clean_num(r.get('MKTCAP'))
        aum_krw = clean_num(r.get('INVSTASST_NETASST_TOTAMT'))
        nav_krw = clean_num(r.get('NAV'))
        close_krw = clean_num(r.get('TDD_CLSPRC'))
        vol = clean_num(r.get('ACC_TRDVOL'))
        val_krw = clean_num(r.get('ACC_TRDVAL'))
        fee = clean_num(r.get('ETF_TOT_FEE'))
        shrs = clean_num(r.get('LIST_SHRS'))
        cu = clean_num(r.get('CU_QTY'))
        fluc_rt = clean_num(r.get('FLUC_RT'))
        chg_krw = clean_num(r.get('CMPPREVDD_PRC'))
        list_dd = str(r.get('LIST_DD', '')).replace('/', '-')

        rec = {
            '티커': str(r.get('ISU_SRT_CD', '')).strip(),
            'ISIN': str(r.get('ISU_CD', '')).strip(),
            'ETF명': str(r.get('ISU_ABBRV', '')).strip(),
            '정식종목명': str(r.get('ISU_NM', '')).strip(),
            '영문명': str(r.get('ISU_ENG_NM', '')).strip(),
            '운용사': str(r.get('COM_ABBRV', '')).strip(),
            '출시일': list_dd,
            '기초지수명': str(r.get('ETF_OBJ_IDX_NM', '')).strip(),
            '지수산출기관': str(r.get('IDX_CALC_INST_NM1', '')).strip(),
            '복제형태': str(r.get('ETF_REPLICA_METHD_TP_CD', '')).strip(),
            '시장분류': str(r.get('IDX_MKT_CLSS_NM', '')).strip(),
            '자산분류': str(r.get('IDX_ASST_CLSS_NM', '')).strip(),
            '과세유형': str(r.get('TAX_TP_CD', '')).strip(),
            '총보수율': fee,
            'CU수량': cu,
            '상장좌수': shrs,
            '현재가_원': close_krw,
            '전일대비_원': chg_krw,
            '등락률_pct': fluc_rt,
            'NAV_원': nav_krw,
            '거래량_주': vol,
            '거래대금_원': val_krw,
            '거래대금_억원': round(val_krw / 1e8, 2),
            '시가총액_원': mktcap_krw,
            '시가총액_억원': round(mktcap_krw / 1e8, 2),
            '순자산총액_원': aum_krw,
            '순자산총액_억원': round(aum_krw / 1e8, 2)
        }
        records.append(rec)

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "etf_list_kr.json")
    csv_path = os.path.join(output_dir, "etf_list_kr.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    df_out = pd.DataFrame(records)
    df_out.to_csv(csv_path, index=False, encoding="utf-8-sig")

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root_dir, "etf_list_kr.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    df_out.to_csv(os.path.join(root_dir, "etf_list_kr.csv"), index=False, encoding="utf-8-sig")

    print(f"  - 완료: {json_path}")
    print(f"  - 완료: {csv_path}")

if __name__ == "__main__":
    run()
'''

fetch_div_code = '''"""
fetch_dividend_history.py
-------------------------
한국예탁결제원 증권정보포털(SEIBRO)의 공식 결제 원장 서블릿 API를 통해
특정 ETF(또는 대표 배당 ETF)의 전회차 분배금 지급 히스토리를 일괄 수집합니다.

사용법:
    D:\\H2\\hermes-agent\\venv\\Scripts\\python.exe scripts/fetch_dividend_history.py
"""

import sys
import json
import os
import requests
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

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

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "selected_etfs_dividend_history.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root_dir, "selected_etfs_dividend_history.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"  - 완료: {out_path} 저장 성공!")

if __name__ == "__main__":
    run()
'''

with open(os.path.join(root, "scripts", "fetch_etf_list.py"), "w", encoding="utf-8") as f:
    f.write(fetch_list_code)

with open(os.path.join(root, "scripts", "fetch_dividend_history.py"), "w", encoding="utf-8") as f:
    f.write(fetch_div_code)

print("Scripts written successfully!")
