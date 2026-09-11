import requests
import xml.etree.ElementTree as ET
import pandas as pd

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

def get_distribution_history(isin, name=""):
    xml_body = f"""<reqParam action="exerInfoDtramtPayStatPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">
    <START_PAGE value="1"/>
    <END_PAGE value="100"/>
    <etf_sort_cd value=""/>
    <etf_big_sort_cd value=""/>
    <isin value="{isin}"/>
    <mngco_custno value=""/>
    <RGT_RSN_DTAIL_SORT_CD value=""/>
    <fromRGT_STD_DT value="20200101"/>
    <toRGT_STD_DT value="20261231"/>
</reqParam>"""

    res = requests.post(url, data=xml_body.encode('utf-8'), headers=headers)
    if res.status_code != 200:
        print(f"Error for {isin}: {res.status_code}")
        return []
    
    root = ET.fromstring(res.text)
    rows = []
    for el in root.iter():
        if el.tag.endswith('result'):
            data = {child.tag: child.attrib.get('value', child.text) for child in el}
            if data:
                rows.append(data)
    return rows

targets = [
    # Top 3 High Dividend ETFs
    ("KR7161510004", "PLUS 고배당주"),
    ("KR7466940004", "TIGER 은행고배당플러스TOP10"),
    ("KR70105E0007", "SOL 코리아고배당"),
    # Top 3 Monthly Income / Covered Call ETFs
    ("KR7498400000", "KODEX 200타겟위클리커버드콜"),
    ("KR7472150002", "TIGER 배당커버드콜액티브"),
    ("KR7486290001", "TIGER 미국나스닥100타겟데일리커버드콜"),
]

for isin, name in targets:
    rows = get_distribution_history(isin, name)
    print(f"=== {name} ({isin}) : 총 {len(rows)}건 분배금 내역 ===")
    if rows:
        df = pd.DataFrame(rows)
        # ESTM_STDPRC: 분배금(1주당 지급액), RGT_STD_DT: 분배기준일, TH1_PAY_TERM_BEGIN_DT: 지급일
        sub = df[['RGT_STD_DT', 'TH1_PAY_TERM_BEGIN_DT', 'ESTM_STDPRC', 'TAXSTD', 'RGT_RSN_DTAIL_NM']]
        sub.columns = ['기준일', '지급일', '주당분배금(원)', '과표기준가', '사유']
        print(sub.head(5).to_string(index=False))
    print()
