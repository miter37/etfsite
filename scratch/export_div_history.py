import requests
import xml.etree.ElementTree as ET
import pandas as pd
import json

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

def get_seibro_history(isin, name):
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

target_etfs = [
    # [대표 배당주 ETF 3선 (전통 배당 및 배당성장)]
    {"category": "대표 배당주", "ticker": "161510", "isin": "KR7161510003", "name": "PLUS 고배당주", "issuer": "한화자산운용"},
    {"category": "대표 배당주", "ticker": "458730", "isin": "KR7458730009", "name": "TIGER 미국배당다우존스", "issuer": "미래에셋자산운용"},
    {"category": "대표 배당주", "ticker": "466940", "isin": "KR7466940004", "name": "TIGER 은행고배당플러스TOP10", "issuer": "미래에셋자산운용"},
    
    # [대표 월지급식(고인컴 커버드콜) ETF 3선]
    {"category": "대표 월지급식(인컴)", "ticker": "498400", "isin": "KR7498400001", "name": "KODEX 200타겟위클리커버드콜", "issuer": "삼성자산운용"},
    {"category": "대표 월지급식(인컴)", "ticker": "472150", "isin": "KR7472150002", "name": "TIGER 배당커버드콜액티브", "issuer": "미래에셋자산운용"},
    {"category": "대표 월지급식(인컴)", "ticker": "441640", "isin": "KR7441640000", "name": "KODEX 미국배당커버드콜액티브", "issuer": "삼성자산운용"}
]

all_results = {}
for target in target_etfs:
    isin = target['isin']
    name = target['name']
    rows = get_seibro_history(isin, name)
    print(f"[{target['category']}] {name} ({isin}): {len(rows)}건")
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

with open("selected_etfs_dividend_history.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("\nSaved to selected_etfs_dividend_history.json successfully!")
