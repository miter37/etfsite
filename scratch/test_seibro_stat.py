import requests
import xml.etree.ElementTree as ET
import pandas as pd

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

xml_body = (
    '<reqParam action="exerInfoDtramtPayStatPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">'
    '<START_PAGE value="1"/>'
    '<END_PAGE value="30"/>'
    '<etf_sort_cd value=""/>'
    '<etf_big_sort_cd value=""/>'
    '<isin value=""/>'
    '<mngco_custno value=""/>'
    '<RGT_RSN_DTAIL_SORT_CD value=""/>'
    '<fromRGT_STD_DT value="20260801"/>'
    '<toRGT_STD_DT value="20260911"/>'
    '</reqParam>'
)

res = requests.post(url, data=xml_body.encode('utf-8'), headers=headers)
print("Status:", res.status_code)
print("Response text length:", len(res.text))

if res.status_code == 200:
    root = ET.fromstring(res.text)
    rows = []
    for el in root.iter():
        if el.tag.endswith('result'):
            data = {child.tag: child.attrib.get('value', child.text) for child in el}
            if data:
                rows.append(data)
    print(f"Parsed {len(rows)} rows.")
    if rows:
        df = pd.DataFrame(rows)
        print("Columns:", df.columns.tolist())
        print(df.head(3))
    else:
        print("Raw XML preview:\n", res.text[:1200])
