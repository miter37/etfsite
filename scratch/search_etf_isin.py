import requests
import xml.etree.ElementTree as ET

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/control.jsp?w2xPath=/IPORTAL/user/etc/BIP_CMUC01039P.xml"
}

# Search ETF list by keyword
def search_etf(keyword):
    xml_body = f"""<reqParam action="searchEtfContentList" task="ksd.safe.bip.cmuc.User.process.SearchPTask">
    <ETF_SORT_CD value=""/>
    <MNGCO_CUSTNO value=""/>
    <KOR_SECN_NM value="{keyword}"/>
</reqParam>"""
    res = requests.post(url, data=xml_body.encode('utf-8'), headers=headers)
    root = ET.fromstring(res.text)
    results = []
    for el in root.iter():
        if el.tag.endswith('result'):
            data = {child.tag: child.attrib.get('value', child.text) for child in el}
            results.append(data)
    return results

for kw in ["PLUS 고배당주", "SOL 미국배당", "KODEX 200타겟위클리"]:
    res = search_etf(kw)
    print(f"=== Keyword: {kw} (Found {len(res)}) ===")
    for r in res:
        print(f"  ISIN: {r.get('ISIN')}, Name: {r.get('KOR_SECN_NM')}, ShortCode: {r.get('SHORT_ISIN')}")
