import requests
import xml.etree.ElementTree as ET

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

xml_body = (
    '<reqParam action="exerInfoDtramtPayStatPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">'
    '<START_PAGE value="1"/>'
    '<END_PAGE value="500"/>'
    '<etf_sort_cd value=""/>'
    '<etf_big_sort_cd value=""/>'
    '<isin value=""/>'
    '<mngco_custno value=""/>'
    '<RGT_RSN_DTAIL_SORT_CD value=""/>'
    '<fromRGT_STD_DT value="20260701"/>'
    '<toRGT_STD_DT value="20260911"/>'
    '</reqParam>'
)

res = requests.post(url, data=xml_body.encode('utf-8'), headers=headers)
root = ET.fromstring(res.text)
found = set()
for el in root.iter():
    if el.tag.endswith('result'):
        data = {child.tag: child.attrib.get('value', child.text) for child in el}
        isin = data.get('ISIN')
        name = data.get('KOR_SECN_NM')
        if any(k in name for k in ['고배당', '배당', '위클리', '커버드콜', '다우존스']):
            if (isin, name) not in found:
                found.add((isin, name))
                print(f"[{isin}] {name}")
