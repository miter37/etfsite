import requests
import xml.etree.ElementTree as ET

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

def test_prog_list(isin, name):
    # Tab 2 in SEIBRO uses exerInfoDtramtPayProgPlist
    xml_body = f"""<reqParam action="exerInfoDtramtPayProgPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">
    <START_PAGE value="1"/>
    <END_PAGE value="100"/>
    <isin value="{isin}"/>
    <fromRGT_STD_DT value="20100101"/>
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
    print(f"[{isin}] {name}: {len(rows)}건")
    if rows:
        print("  Sample row:", rows[0])
    return rows

test_prog_list("KR7161510004", "PLUS 고배당주")
test_prog_list("KR7458730009", "TIGER 미국배당다우존스")
test_prog_list("KR7446720002", "SOL 미국배당다우존스")
test_prog_list("KR7472150002", "TIGER 배당커버드콜액티브")
test_prog_list("KR7498400000", "KODEX 200타겟위클리커버드콜")
