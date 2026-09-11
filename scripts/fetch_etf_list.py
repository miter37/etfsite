"""
fetch_etf_list.py
-----------------
한국거래소(KRX) 공인 백엔드를 통해 국내 상장된 전체 ETF(1,160+개)의
마스터 메타데이터와 당일 종가/시가총액/NAV를 일괄 수집하여 저장합니다.

사용법:
    D:\H2\hermes-agent\venv\Scripts\python.exe scripts/fetch_etf_list.py
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
