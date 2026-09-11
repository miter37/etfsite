# AGENTS.md - ETF Data Collection & Analysis Playbook

이 문서는 `etfsite` 프로젝트에서 실제 검증에 성공한 **한국 ETF 데이터 수집, 가공 및 분배금 히스토리 추출 방식**을 정리한 운영 가이드다. 어떤 작업을 수행할 때 어떤 소스와 스크립트를 사용하면 되는지 명확히 기술한다.

---

## 1. 실행 환경 원칙

* **파이썬 인터프리터 경로**:  
  `C:\Python313\python.exe` (또는 `python.exe`)
* **단위 규율 (`etfsite_AGENT_MUSTREAD.md` C8)**:  
  * 변수명에 단위 접미사 강제 (`_krw`, `_eok`, `_jo`).
  * 저장은 원(KRW) 단위 정수로, 환산(억원/조원)은 출력/저장 직전 1회만 변환.
  * 네이버 API의 `marketSum`은 **백만원** 단위 (`/ 1e4` = 억원, `* 1e6` = 원).

---

## 2. 작업별 성공 방식 및 스크립트 가이드

### 2.1 한국 전체 ETF 마스터 및 당일 시세/시총 수집
* **목적**: 국내 상장된 전체 ETF(1,160+개)의 티커, ISIN, 정식명, 운용사, 기초지수, 보수율, 상장일, 현재가, NAV, 시가총액, 거래대금 일괄 수집.
* **성공 소스**: KRX 공인 백엔드 (`pykrx.website.krx.etx.core`)
  * `ETF_전종목기본종목().fetch()`: 공식 마스터 메타데이터
  * `전종목시세_ETF().fetch(YYYYMMDD)`: 당일 확정 시세/시가총액/거래대금
* **산출물**:
  * [`etf_list_kr.json`](file:///C:/AI/etfsite/outputs/etf_list_kr.json) (전체 JSON DB)
  * [`etf_list_kr.csv`](file:///C:/AI/etfsite/outputs/etf_list_kr.csv) (분석용 CSV)
* **실행 스크립트**:
```bash
C:\Python313\python.exe scripts/fetch_etf_list.py
```

---

### 2.2 ETF 공식 분배금(배당금) 지급 히스토리 및 배당 스크리너
* **목적**: 특정 ETF의 과거 전회차 분배금 지급일, 기준일, 1주당 분배금(원), 분배율(%), 과표기준가 수집 및 배당수익률 랭킹 스크리닝.
* **성공 소스**: 한국예탁결제원 증권정보포털 SEIBRO (`BIP_CNTS06030V` 서블릿)
  * 웹 스크래핑 대비 차단이 없고 공식 결제 원장 기준으로 과거 전 시계열 제공.
  * 단축 티커(예: `458730`) 입력 시 Luhn 알고리즘으로 풀 ISIN(`KR7458730009`)을 자동 역산하여 호출.

#### A. 단일 종목 분배금 히스토리 (또는 대표 6종 기본 실행)
* **산출물**:
  * [`outputs/{ticker}_dividend_history.json`](file:///C:/AI/etfsite/outputs/458730_dividend_history.json) (단일 종목 조회 시)
  * [`outputs/selected_etfs_dividend_history.json`](file:///C:/AI/etfsite/outputs/selected_etfs_dividend_history.json) (대표 6선 기본 실행 시)
* **실행 스크립트**:
```bash
# 특정 ETF 단일 조회 (예: TIGER 미국배당다우존스 458730)
C:\Python313\python.exe scripts/fetch_dividend_history.py --ticker 458730

# 대표 6선(고배당 및 월지급식 대표주) 일괄 수집
C:\Python313\python.exe scripts/fetch_dividend_history.py
```

#### B. 배당/인컴 ETF 자동 스크리너 및 랭킹 산출
* **목적**: `etf_list_kr.json`의 고배당/커버드콜/인컴 ETF를 선별하여 최근 1년간 지급된 주당 분배금 합계, 시가 배당수익률(%), 배당주기(월배당 여부)를 자동 계산하여 랭킹화.
* **산출물**:
  * [`outputs/dividend_screener_ranking.csv`](file:///C:/AI/etfsite/outputs/dividend_screener_ranking.csv)
  * [`outputs/dividend_screener_ranking.json`](file:///C:/AI/etfsite/outputs/dividend_screener_ranking.json)
* **실행 스크립트**:
```bash
C:\Python313\python.exe scripts/fetch_dividend_screener.py --top 25
```

#### C. 연도-월별 분배금 및 당시 주가 대비 실질 배당수익률 분석 (기본 최근 2년)
* **목적**: 특정 ETF의 최근 N년(기본값 2년)간 매월 지급된 주당 분배금과 **지급기준일 당시 종가**를 1:1 매칭하여 실질 월별 배당수익률(%), 연환산 수익률, 연도별 누적 합계 및 현재가 대비 누적 회수율을 정밀 계산.
* **성공 소스**: SEIBRO 결제원 원장(`BIP_CNTS06030V`) + `pykrx` 네이버 백엔드 일별 확정 종가.
* **산출물**:
  * [`outputs/{ticker}_dividend_monthly_{years}y.csv`](file:///C:/AI/etfsite/outputs/458730_dividend_monthly_2y.csv)
  * [`outputs/{ticker}_dividend_monthly_{years}y.json`](file:///C:/AI/etfsite/outputs/458730_dividend_monthly_2y.json)
* **실행 스크립트**:
```bash
# 기본 2년 분석 (TIGER 미국배당다우존스 458730)
C:\Python313\python.exe scripts/fetch_dividend_monthly.py --ticker 458730 --years 2

# 1년 분석 (KODEX 200타겟위클리커버드콜 498400)
C:\Python313\python.exe scripts/fetch_dividend_monthly.py --ticker 498400 --years 1

# 3년 장기 분석 (PLUS 고배당주 161510)
C:\Python313\python.exe scripts/fetch_dividend_monthly.py --ticker 161510 --years 3
```

---

### 2.3 ACE 운용사 실시간 Live AUM & Holdings (PDF) 수집
* **목적**: ACE ETF 전용 실시간 API를 통해 장중/확정 순자산총액(AUM, 원 단위 정수), **공식 6자리 주식코드(`jm_KSC_CD`)가 포함된 실시간 PDF 편입종목**, 최근 분배금을 무차단으로 수집.
* **특징**:
  * 거래소 PDF 화면(`m.krx` `030302`)은 종목명만 제공되어 동명이인 매핑이 필요하지만, ACE API는 **정식 6자리 종목코드**를 바로 제공함.
  * `nastAmt`: 원 단위 확정 펀드 전체 AUM.
  * `val_AM`: 1 CU당 평가금액(전체 AUM 아님, `MUSTREAD` 라인 82).
* **산출물**:
  * [`outputs/ace_{ticker}_live_holdings.csv`](file:///C:/AI/etfsite/outputs/ace_469150_live_holdings.csv)
  * [`outputs/ace_{ticker}_live_summary.json`](file:///C:/AI/etfsite/outputs/ace_469150_live_summary.json)
* **실행 스크립트**:
```bash
# 특정 ACE ETF 실시간 수집 (기본값: 469150 ACE AI반도체TOP3+)
C:\Python313\python.exe scripts/fetch_ace_live.py --ticker 469150

# 전체 ACE ETF 마스터 요약 저장
C:\Python313\python.exe scripts/fetch_ace_live.py --all
```

---

### 2.4 ETF 개별 시세·NAV·상장좌수 및 당일 PDF 보유종목 수집
* **목적**: 특정 ETF의 최근 일별 시고저종, 거래량, 확정 NAV, 괴리율, 상장좌수 및 설정환매 내역, 당일 최신 PDF 편입종목 수집.
* **성공 소스**: 
  * 시세(시고저종/거래량): `pykrx.stock.get_market_ohlcv(start_date, end_date, ticker)` (네이버 금융 백엔드 기반으로 무차단 안정적 수집)
  * NAV/괴리율: `m.krx.co.kr` 모바일 그리드 `030305` (`hpetp030305m01`)
  * 상장좌수/설정환매: `m.krx.co.kr` 모바일 그리드 `030301` (`hpetp030301m02`)
  * 당일 PDF 편입종목: `m.krx.co.kr` 모바일 그리드 `030302` (`hpetp030302m01`)
* **산출물**:
  * [`outputs/{ticker}_price_history_3m.csv`](file:///C:/AI/etfsite/outputs/069500_price_history_3m.csv) (일별 시세/NAV/좌수 통합)
  * [`outputs/{ticker}_latest_pdf.csv`](file:///C:/AI/etfsite/outputs/069500_latest_pdf.csv) (당일 전체 편입종목 및 비중)
* **실행 스크립트**:
```bash
C:\Python313\python.exe scripts/fetch_etf_price_history.py --ticker 069500 --days 90
```

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
