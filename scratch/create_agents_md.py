content = """# AGENTS.md - ETF Data Collection & Analysis Playbook

이 문서는 `etfsite` 프로젝트에서 실제 검증에 성공한 **한국 ETF 데이터 수집, 가공 및 분배금 히스토리 추출 방식**을 정리한 운영 가이드다. 어떤 작업을 수행할 때 어떤 소스와 스크립트를 사용하면 되는지 명확히 기술한다.

---

## 1. 실행 환경 원칙

* **파이썬 인터프리터 경로**:  
  `D:\\H2\\hermes-agent\\venv\\Scripts\\python.exe` (시스템 기본 python 대신 해당 venv 사용)
* **단위 규율 (`etfsite_AGENT_MUSTREAD.md` C8)**:  
  * 변수명에 단위 접미사 강제 (`_krw`, `_eok`, `_jo`).
  * 저장은 원(KRW) 단위 정수로, 환산(억원/조원)은 출력/저장 직전 1회만 변환.
  * 네이버 API의 `marketSum`은 **백만원** 단위 (`/ 1e4` = 억원).

---

## 2. 작업별 성공 방식 및 스크립트 가이드

### 2.1 한국 전체 ETF 마스터 및 당일 시세/시총 수집
* **목적**: 국내 상장된 전체 ETF(1,160+개)의 티커, ISIN, 정식명, 운용사, 기초지수, 보수율, 상장일, 현재가, NAV, 시가총액, 거래대금 일괄 수집.
* **성공 소스**: KRX 공인 백엔드 (`pykrx.website.krx.etx.core`)
  * `ETF_전종목기본종목().fetch()`: 공식 마스터 메타데이터
  * `전종목시세_ETF().fetch(YYYYMMDD)`: 당일 확정 시세/시가총액/거래대금
* **산출물**:
  * [`etf_list_kr.json`](file:///D:/APPs/etfsite/etf_list_kr.json) (전체 JSON DB)
  * [`etf_list_kr.csv`](file:///D:/APPs/etfsite/etf_list_kr.csv) (분석용 CSV)
* **핵심 실행 코드 패턴**:
```python
from pykrx.website.krx.etx import core
import pandas as pd
import datetime

# 1. 마스터 메타데이터 수집
df_master = core.ETF_전종목기본종목().fetch()

# 2. 당일 시세 및 시가총액 결합
today_str = datetime.date.today().strftime('%Y%m%d')
df_market = core.전종목시세_ETF().fetch(today_str)

merged = pd.merge(df_master, df_market, on='ISU_SRT_CD', how='left')
```

---

### 2.2 ETF 공식 분배금(배당금) 지급 히스토리 수집
* **목적**: 특정 ETF의 과거 전회차 분배금 지급일, 기준일, 1주당 분배금(원), 분배율(%), 과표기준가 수집.
* **성공 소스**: 한국예탁결제원 증권정보포털 SEIBRO (`BIP_CNTS06030V` 서블릿)
  * 웹 스크래핑 대비 차단이 없고 공식 원장 기준으로 과거 전 시계열 제공.
  * 액션: `exerInfoDtramtPayProgPlist` (태스크: `ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask`)
* **필수 주의사항**:
  * 단축 티커(예: `161510`)가 아닌 **공식 풀 ISIN(예: `KR7161510003`)**을 입력해야 함.
  * ETF마다 체크디짓 규칙 차이가 있을 수 있으므로 SEIBRO ETF 검색(`BIP_CMUC01039P`)을 통해 매핑된 ISIN을 사용.
* **산출물**:
  * [`selected_etfs_dividend_history.json`](file:///D:/APPs/etfsite/selected_etfs_dividend_history.json) (대표 6종 분배금 전체 이력)
* **핵심 실행 코드 패턴**:
```python
import requests
import xml.etree.ElementTree as ET

url = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/xml; charset=UTF-8",
    "Referer": "https://seibro.or.kr/websquare/websquare.jsp?w2xPath=/IPORTAL/user/etf/BIP_CNTS06030V.xml"
}

xml_body = f'''<reqParam action="exerInfoDtramtPayProgPlist" task="ksd.safe.bip.cnts.etf.process.EtfExerInfoPTask">
    <START_PAGE value="1"/>
    <END_PAGE value="100"/>
    <isin value="{isin}"/>
    <fromRGT_STD_DT value="20150101"/>
    <toRGT_STD_DT value="20261231"/>
</reqParam>'''

res = requests.post(url, data=xml_body.encode('utf-8'), headers=headers)
root = ET.fromstring(res.text)
# el.findtext('ESTM_STDPRC'): 주당분배금(원)
# el.findtext('RGT_STD_DT'): 분배기준일
# el.findtext('TH1_PAY_TERM_BEGIN_DT'): 실지급일
```

---

### 2.3 빠른 시세/목록 스냅샷 조회 (네이버 금융)
* **목적**: 인증 없이 초고속으로 전종목 단순 시세 및 탭별 분류 스냅샷 확인.
* **엔드포인트**: `https://finance.naver.com/api/sise/etfItemList.nhn`
* **주의**: `marketSum`은 **백만원** 단위이므로 `* 1_000_000` 후 `_krw`로 저장.

---

### 2.4 ACE 운용사 실시간 Live AUM & Holdings (PDF) 조회
* **목적**: ACE ETF의 당일 장중/확정 AUM 및 전 편입종목 실시간 비중 확인.
* **엔드포인트**:
  * 메타/AUM: `https://papi.aceetf.co.kr/api/funds/{fundCd}` (`nastAmt` = 원 단위 확정 AUM)
  * 실시간 PDF: `https://papi.aceetf.co.kr/api/funds/{fundCd}/pdf?size=50`
  * 분배금: `https://papi.aceetf.co.kr/api/funds/{fundCd}/dividend?size=100`

---

## 3. 대표 ETF 벤치마크 6선 레퍼런스

| 구분 | 티커 | ISIN | 종목명 | 운용사 | 특성 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **대표 배당주** | `458730` | `KR7458730009` | TIGER 미국배당다우존스 | 미래에셋 | 배당 ETF 시총 1위, 한국판 SCHD |
| **대표 배당주** | `161510` | `KR7161510003` | PLUS 고배당주 | 한화 | 국내 주식형 전통 고배당 시총 1위 |
| **대표 배당주** | `466940` | `KR7466940004` | TIGER 은행고배당플러스TOP10 | 미래에셋 | 4대 금융지주 및 은행주 집중 |
| **대표 월지급식** | `498400` | `KR7498400001` | KODEX 200타겟위클리커버드콜 | 삼성 | 국내 옵션 타겟 프리미엄 시총 1위 |
| **대표 월지급식** | `472150` | `KR7472150002` | TIGER 배당커버드콜액티브 | 미래에셋 | 국내 우량 배당주 + 커버드콜 액티브 |
| **대표 월지급식** | `441640` | `KR7441640000` | KODEX 미국배당커버드콜액티브 | 삼성 | 미국 배당주 + 콜옵션 매도 월지급 |
"""

with open(r"D:\APPs\etfsite\AGENTS.md", "w", encoding="utf-8") as f:
    f.write(content)
print("D:\\APPs\\etfsite\\AGENTS.md written successfully.")
