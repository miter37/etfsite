import requests
import xml.etree.ElementTree as ET
import pandas as pd

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

# 161510 isin: KR7161510004
xml_body = (
    '<reqParam action="exerInfoDtramtPayProgPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">'
    '<START_PAGE value="1"/>'
    '<END_PAGE value="100"/>'
    '<isin value="KR7161510004"/>'
    '<fromRGT_STD_DT value="20200101"/>'
    '<toRGT_STD_DT value="20261231"/>'
    '</reqParam>'
)

res = requests.post(url, data=xml_body.encode('utf-8'), headers=headers)
print("Status:", res.status_code)
print("Response text length:", len(res.text))

if res.status_code == 200:
    root = ET.fromstring(res.text)
    rows = []
    # Search for record elements
    for el in root.findall('.//record'):
        data = {child.tag: child.attrib.get('value', child.text) for child in el}
        rows.append(data)
    if not rows:
        for el in root.iter():
            if len(el) > 3:
                data = {child.tag: child.attrib.get('value', child.text) for child in el}
                rows.append(data)
    print(f"Parsed {len(rows)} rows.")
    if rows:
        df = pd.DataFrame(rows)
        print("Columns:", df.columns.tolist())
        print(df.iloc[0].to_dict())
    else:
        print("Raw XML preview:\n", res.text[:1000])
