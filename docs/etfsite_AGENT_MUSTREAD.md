---
name: etf-doc-info
description: Canonical operating and reference guide for Korean ETF document collection, ETF_info0.json methodology modeling, PDF/NAV interpretation, data-quality controls, and FnGuide/FICS data rules.
---

# ETF Document, Data, Methodology & Rebalance Reconstruction Guide

이 문서는 ETF 리밸런싱 분석 프로젝트의 **canonical 운영·검증 문서**다. 규칙은 가능한 한 한 곳에만 상세히 두고, 여러 곳에 적용되는 일반 원칙을 앞에 배치했다. 특정 ETF·특정 데이터 소스에서만 적용되는 예외와 실측 사례는 뒤쪽에 둔다.

문서의 핵심 목적은 단순한 ETF 정보 요약이 아니다. 공식 문서와 검증 가능한 시장 데이터를 이용해 **언제 지수가 바뀌는지, 어떤 종목이 들어오고 나가는지, 어떤 비중이 적용되는지를 재구성하고 과거 정기변경으로 검증한 뒤 다음 리밸런싱을 추정**하는 것이다.

전체 흐름은 다음과 같다.

1. 기존 프로젝트 자산과 canonical source를 먼저 확인한다.
2. 공식 투자설명서·지수방법론을 확보하고 `ETF_info0.json`에 계산 가능한 형태로 구조화한다.
3. PDF/NAV와 시장데이터의 시점·단위·기업행위·결측 문제를 정합성 검증한다.

> **문서 사용 원칙**: 중복된 설명보다 아래의 canonical 위치를 우선한다. 기존 코드나 과거 문서가 `A1`, `B1`, `C8`, `G7` 같은 레거시 참조를 사용하므로 해당 식별자는 본문에 유지했다. 원문에 중복되어 있던 두 번째 `C10`은 FnGuide 특수 규칙 묶음인 `FG1~FG3`으로 정리했다.


---

## 1. 최우선 공통 원칙

이 장의 규칙은 ETF 종류나 산출기관에 관계없이 가장 먼저 적용한다. 세부 API나 특정 지수 사례보다 우선한다.

**1.1 작업 시작 전 기존 자산부터 확인**

외부 웹 검색이나 스크래핑 전에 다음 프로젝트 자산을 먼저 확인한다.

- **`ETF_info0.json` — 메타데이터 및 지수방법론 표준 DB**  
  경로: `D:\ETF_rebal\ETF_info0.json`  
  국내 주요 ETF의 기초지수명, 산출기관, 유니버스 포함/제외 조건, 종목선정 룰, 비중산정 산식(CAP/고정비중), 정기/수시 리밸런싱 일정, 필요 데이터 정의가 정형화되어 있다.
- **`docs/` — 공식 투자설명서 및 지수방법론 원본 PDF 보관소**  
  경로: `D:\ETF_rebal\docs\`  
  이미 저장된 공식 문서를 인터넷에서 다시 받기 전에 반드시 먼저 읽는다.
- **`docs/*FICS업종분류.xlsx` — 공식 FICS 원천 DB (새 데이터 필요 시 SEIBRO 폴백)**  
  `docs/코스피 FICS업종분류.xlsx`에는 코스피 834개사, `docs/코스닥 FICS업종분류.xlsx`에는 코스닥 1,819개 전종목의 공식 코드, 종목명, 시가총액, 대분류·중분류·소분류가 들어 있다. FnGuide 계열 지수에서 FICS를 요구하면 이것이 canonical source다. WICS·포털 업종을 임의 대체하지 않는다. 세부 슬롯 자격 규칙은 `FG1`을 따른다.  
  *만약 시간이 지나 FICS 업종 데이터를 최신 일자로 새로 구하거나 갱신해야 할 경우, 한국예탁결제원 증권정보포털 **SEIBRO (https://seibro.or.kr/)**에서 주식·업종 분류 데이터를 다운로드받아 갱신한다.*

새로운 ETF 분석이나 리밸런싱 계산 요청이 오면 **`ETF_info0.json` → `docs/{종목명}_지수방법론.pdf` → 필요한 공식 원천 데이터** 순으로 확인한다. 이미 구축된 데이터를 재수집하느라 시간을 낭비하거나, 정의된 방법론을 무시하고 계산식을 임의 추정하지 않는다.

**1.2 데이터 품질 등급 — 모든 데이터 항목에 적용**

**F3. 등급 체계**

유동비율뿐 아니라 **모든 데이터 항목에** 등급을 붙인다.

```text
공식          발행처 원본 그대로 (KRX PDF, 방법론, KRX NAV)
공식·전종목    위에 더해 부분관측이 아님이 확인됨
공식역산      공식 자료에서 산술적으로 유도 (지수반영주식수 → 유동비율, C5)
추정          신뢰 가능한 제3자 계산값 (WiseReport 유동비율)
proxy         정의가 다른 대용품 (WICS ↔ FICS/GICS)
현재값만       시계열이 없고 조회 시점 값뿐 (상장주식수) — 과거 계산에 쓰면 기준일 불일치
대체          산식으로 만든 값 (종가×거래량, 종가×현재주식수) — 산식을 함께 표기
미확인        확보 실패. 추정으로 메우지 말 것
``` 

**1.3 단위 규율 — 금액 계산의 최우선 검증**

**C8. 단위 — 거래대금·시가총액에서 가장 흔한 실수**

**이 프로젝트에서 가장 자주 재발한 오류다.** 출처마다 단위가 다르고, 틀려도 숫자가 그럴듯해서
검산하지 않으면 절대 안 잡힌다. 100배 또는 1억배 틀린 보고서가 나온다.

**출처별 단위 (실측 확인)**

| 출처 | 항목 | 단위 | 억원 환산 |
|---|---|---|---|
| pykrx `get_market_ohlcv` | 종가 | **원** | `/1e8` |
| pykrx `get_market_ohlcv` | 거래량 | **주** | 금액 아님 |
| 종가 × 거래량 (거래대금 대체계산) | 금액 | **원** | `/1e8` |
| KRX PDF (m.krx 030302) | 평가금액 | **원** | `/1e8` |
| KRX 지수구성종목 (030303) | 유동시가총액 | **원** | `/1e8` |
| KRX NAV (030305) | 1좌당 순자산가치 | **원** | `× 좌수 / 1e8` |
| KRX 설정·환매 (030301) | 발행수익증권수 | **좌** | 금액 아님 |
| 네이버 `etfItemList` | `marketSum` | **백만원** | `/1e4` |
| WiseReport 기업개요 | 시가총액 | **억원** | 그대로 |
| 네이버 금융 종목페이지 | 상장주식수 | **주** | 금액 아님 |
| ACE API (`/api/funds/{fundCode}`) | `nastAmt` | **원** | `/1e8` (펀드 전체 AUM) |
| ACE API PDF (`/api/funds/.../pdf`) | `val_AM` | **원** | `/1e8` (**1 CU당 평가액, 전체 AUM 아님 ⚠️**) |

가장 흔한 두 실수:

```text
네이버 marketSum 10,802  →  "10,802억" 로 읽음        (실제 108억, 100배 과대)
종가×거래량 3,701,309,xxx →  "37억" 으로 나눠야 하는데
                            /1e4 해서 "37만" 또는 그대로 "37억원" 표기 누락
```

**규율 세 가지**

**① 변수명에 단위를 박는다.** 예외 없이.

```python
adv_krw       = close * volume          # 원
adv_eok       = adv_krw / 1e8           # 억원
mktcap_eok    = mktcap_krw / 1e8
aum_jo        = aum_krw / 1e12          # 조원
```

접미사 없는 금액 변수(`amount`, `value`, `trade`)는 금지한다.
표·CSV 컬럼명도 같다 — `trade_amount_krw`, `adv_1m_eok` 처럼 쓴다.

**② 저장은 원 단위로, 환산은 출력 직전에 한 번만.**
중간 계산에서 억으로 바꾸면 다음 단계에서 또 나누는 이중환산이 생긴다.

**③ 반드시 검산한다.** 단위 오류는 아래 셋 중 하나에 즉시 걸린다.

```text
검산 1  Σ(PDF 평가금액) ÷ NAV = CU당 좌수(K)
        → 50,000 / 20,000 같은 라운드 넘버가 나와야 한다.
          단위가 틀리면 5억이나 0.0005 같은 값이 나온다. 가장 강력한 단위 검증기다.

검산 2  개별 종목 일 거래대금의 상식 범위
        → 삼성전자·SK하이닉스급이 일 1~13조. 중소형주는 수십~수백억.
          어떤 종목이 일 수천조로 나오면 단위 오류다.

검산 3  ETF 순자산총액 = NAV × 상장좌수
        → 알려진 AUM 규모(네이버 시가총액 등)와 같은 자릿수인지 대조.
```

**보고서에 금액을 쓸 때는 숫자마다 단위를 붙인다.** `+3,336.3억`처럼.
단위 없는 숫자는 검토자가 검증할 수 없다.

**1.4 분석 태도와 가설 검증 원칙**

- **회귀 계수 하나로 압축하면 정보가 사라진다.** 기울기 하나로 요약해 "노이즈"라고 치웠다가
  일자별 시계열과 누적으로 다시 보니 다른 그림이 나온 사례가 있었다.
- **강건성 교차검정을 반드시 건다.** 일별 회귀 1.0084(t=3.04)와 누적 텔레스코핑 0.9733이
  방향까지 반대로 나왔다. 한 방향으로만 계산하면 인공물을 믿게 된다.
- **노이즈의 출처를 모르면 탐지 한계를 말할 수 없다.** 노이즈를 9bp에서 3bp로 줄이면
  검출력이 3배가 된다. 이상치 판정보다 노이즈 규명이 먼저다.
- **자동 판정 규칙은 전수 대조로 검증한다.** 기업행위 자동탐지가 평범한 매매를 오분류해
  결과를 악화시킨 사례가 있었다. 후보를 전부 뽑아 눈으로 확인하고 화이트리스트로 고정하는 편이 낫다.

**E1. 관측 안 되는 필터로 잔여 오차를 메우면 순환논증이다**

모델이 과거를 재현하지 못할 때 **"관측 불가능한 필터에서 이 종목들이 탈락했다"** 고 놓으면 항상 맞출 수 있다.
자유도가 오차 개수만큼 있기 때문이다. **자유도가 오차 수만큼 있는 설명은 설명이 아니다.**

검정법은 **시점 간 안정성**이다. 같은 방식을 여러 정기변경에 적용해 제외집합을 각각 뽑고, 구성이 유지되는지 본다.

```text
안정적    → 구조적 제외(업종·자격 요건). 설명력 있고 다음 회차 예측에 쓸 수 있다
매번 바뀜 → 사후 적합. 예측력 없음. 모델의 계통오차를 다른 이름으로 부른 것뿐
```

실측: 4개 정기변경에서 제외집합이 5·3·6·7종목으로 나왔고 **항상 제외되는 종목이 하나도 없었다.**
12개 종목이 제외↔편입을 오갔다. 이 경우 "매출필터 탈락"이라는 설명은 폐기해야 한다.

**E2. 산식 용어의 다의성은 과거 재현으로 판별되지 않을 수 있다**

`0.5 × A비중 + 0.5 × B비중` 같은 산식에서 **"비중"의 정의가 방법론에 없는 경우**가 흔하다.
해석 후보를 전부 구현해 과거 재현율을 비교했더니 **네 해석이 55/60으로 전부 동일**한데
현재 시점 답은 갈렸다(합계대비 몫·순위점수·최대값정규화는 A종목, 로그 z-score는 B종목).

```text
A 합계대비 몫    : 0.5·Aᵢ/ΣA + 0.5·Bᵢ/ΣB
B 순위점수       : 0.5·rank%(A) + 0.5·rank%(B)
C 최대값 정규화   : 0.5·Aᵢ/max(A) + 0.5·Bᵢ/max(B)
D 로그 z-score   : 0.5·z(lnA) + 0.5·z(lnB)      ← 스케일을 압축해 대형주 우위가 살아난다
```

**"과거를 잘 맞혔으니 미래도 맞다"가 성립하지 않는 구조다.**
재현 테스트가 판별하지 못하는 자유도를 찾아 보고서에 명시하고, 갈리는 지점을 함께 제시한다.
문언상 가장 자연스러운 해석(`비중` = 합계대비 몫)을 base로 두되 단정하지 않는다.

**E3. `0.5×A비중 + 0.5×B비중`의 실질 가중치는 0.5:0.5가 아니다**

ΣA와 ΣB의 크기가 다르면 **그 배수가 실질 가중치**다.

```text
score = 0.5·Aᵢ/ΣA + 0.5·Bᵢ/ΣB   ⟹   순위 ∝ Aᵢ + (ΣA/ΣB)·Bᵢ
```

실측: 시가총액 풀 3,370조 / 거래대금 풀 24.5조 = **138배**.
거래대금 1원이 시가총액 138원 값을 한다. 그래서 시총 2.75배 열세인 종목이 거래대금 1.58배 우위로 역전했다.

배수를 지배하는 건 **상위 소수 종목의 집중도 차이**다. 같은 표본에서 상위 2종목이
시가총액의 92.8%를 차지하는 반면 거래대금은 81.4%였다. 중소형주는 구조적으로
거래대금 비중이 시총 비중보다 크게 잡히고, 그 격차가 클수록 유리해진다.

> **시가총액과 거래대금을 섞는 스코어를 만나면 `Σ분자1/Σ분자2` 배수를 먼저 계산하라.**
> 안 하면 "50:50이니 시총 2배면 이기겠지"로 정반대 결론이 난다.
> 유동시총으로 바꾸면 ΣA가 줄어 배수가 내려가고 거래대금 항이 더 세진다 — 방향을 직접 계산해 확인할 것.

**E4. 방법론의 재량 조항을 먼저 읽고 구간을 나눠라**

지수 방법론에는 정량 규칙 뒤에 **재량 조항**이 붙는 경우가 많다. 실제 문구 예:

> "**최종 구성종목을 선정한 이후** (…) 최종 선정된 기업들의 실제 산업 내 지위 등이 해당 지수와
> 어긋나지 않는지 **운용사 및 애널리스트, 관련 업계 전문가의 의견을 반영**할 계획"
> — FnGuide AI 반도체 TOP3+ 방법론 Appendix D

이런 조항이 있으면 **하위 순위 구간의 예측 불가능성은 데이터 부족이 아니라 구조적**이다.
자료를 더 모아도 좁혀지지 않는다. 실측에서도 상위 5위 구간은 4회 모두 100% 재현된 반면
하위 구간에는 스코어로 설명되지 않는 계통오차가 남았다(스코어 27위 종목이 19위 종목을 제치고 4회 연속 생존).

> **재량이 닿는 구간과 닿지 않는 구간을 나눠 신뢰도를 다르게 매긴다.**
> 그리고 불확실성의 성격을 구분해 쓴다 — "데이터가 없어서 모른다"와
> "재현 불가능한 재량이 개입해서 모른다"는 후속 조치가 완전히 다르다.

**1.5 결과 표현 규율**

**F5. 표현 규율**

- **미확보 항목은 추정으로 메우지 말고 보고서에서 빼거나 `미확인`으로 남긴다.**
  개별주식선물 상장 여부를 못 받았으면 그 열을 통째로 빼는 편이, 검증 안 된 매핑을
  실어 두는 것보다 낫다.
- **이전 작업물의 데이터를 계승할 때는 재검증하거나 계승했다고 명시한다.**
  이전 판의 선물 매핑 17종목을 재검증 없이 그대로 옮긴 사례가 있었다.
- **"없다"가 아니라 "검출 한계 이상은 없다"로 쓴다.** 검출 한계를 금액으로 함께 적는다.
- **결측은 개수와 성격을 함께 적는다.** "267/274 (결측 7, 전부 초소형주)" 처럼.
  개수만 적으면 그 결측이 결론에 영향을 주는지 판단할 수 없다.

---

## 2. ETF 문서 수집과 `ETF_info0.json` 방법론 DB

이 장은 새로운 ETF를 프로젝트에 등록하거나 기존 ETF의 공식 문서·방법론 정보를 갱신할 때 적용한다. 목적은 문서를 보관하는 것이 아니라 **향후 실제 리밸런싱 계산이 가능하도록 규칙을 구조화하는 것**이다.

**Goal**

Given one or more ETF names or tickers, collect the ETF's official prospectus and underlying index methodology, save both PDFs under `docs/`, read the methodology, and update `ETF_info0.json` so the ETF's constituent-selection and weighting rules can be reconstructed later.

**User Intent**

The purpose is not only to archive PDFs or summarize ETF facts. The user is building a structured dataset that can later be used to estimate, for any given date, what constituents an ETF's underlying index should hold and what weights those constituents should have.

When filling `ETF_info0.json`, optimize for future calculation:

- Identify **when** the index changes: selection dates, weight fixing dates, effective dates, regular rebalance cycles, and special rebalance triggers.
- Identify **which stocks** enter or leave: universe filters, ranking criteria, buffer rules, new-listing rules, deletion rules, committee overrides, and replacement rules.
- Identify **how weights** are set: market-cap weighting, free-float weighting, fixed top weights, equal weighting, caps, trigger thresholds, post-adjustment caps, and excess-weight redistribution.
- Identify **what external data** is needed to reproduce the methodology: price, market cap, free float, trading value, FICS/GICS classification, sales data, text-mining score, index membership, event calendars, and option/futures expiry dates.
- Preserve ambiguity and discretion instead of hiding it. If exact reconstruction requires unavailable data or committee judgment, record that in the JSON.

The final JSON should be useful to someone who has market data and wants to compute an expected rebalance, not merely to someone reading a product description.

**Existing ETF Check**

Before downloading or editing, inspect `ETF_info0.json` if it exists.

- Match existing ETFs by `티커` first, then by `이름`.
- If the ETF already exists, stop and ask the user whether to overwrite/re-download and update the existing entry.
- Do not overwrite existing PDFs or JSON entries for an existing ETF without user confirmation.
- If the ETF is new, proceed without asking.

**Output Locations**

Create `docs/` if missing.

Save files as:

```text
docs/{종목명}_투자설명서.pdf
docs/{종목명}_지수방법론.pdf
```

Use the exact ETF display name chosen for `ETF_info0.json`.

Update or create:

```text
ETF_info0.json
```

**Source Priority**

Use current official or primary sources. Browse because ETF documents, fund IDs, methodology versions, and prospectuses change.

Preferred sources:

- ETF issuer official site for prospectus:
  - TIGER: Mirae Asset TIGER ETF site
  - KODEX: Samsung Fund/KODEX site
  - SOL: SOL ETF/Shinhan site
  - HANARO: HANARO ETF site
  - ACE: ACE ETF/Korea Investment site
- Index provider official site for methodology:
  - FnGuide index methodology page and file server
  - KRX index methodology or official KRX-linked methodology PDF
  - Other index provider official methodology pages if the ETF uses a non-FnGuide/non-KRX index

If an official site uses a tokenized download flow, inspect the page JavaScript or API calls and use the token flow rather than saving an HTML error page.

**Practical Source Tips**

Issuer and index-provider sites often use predictable but undocumented routes. Verify each result before relying on it.

- **FnGuide methodology**
  - The public methodology page may be a JavaScript app. Inspect network/API calls if links are not visible in HTML.
  - A useful pattern seen before:
    - API: `POST https://www.fnindex.co.kr/api/getData`
    - Body: `{"url":"/RS/list/book","params":{"gb":"TIS"}}`
    - File base: `https://file.fnguide.com/fnindex/files/`
  - Match by exact index name, not ETF name. Similar names can refer to different indices, for example `AI반도체TOP2플러스` vs `AI반도체 TOP2+`.

- **SOL ETF**
  - Prospectus downloads may require a token.
  - Inspect `/static/pc/js/.../fileDownload.js` or similar scripts.
  - A useful pattern seen before:
    - metadata: `/api/etf/pds/policyDescription/{fundCode}`
    - token: `/file/token/fund?fundCode={fundCode}&downloadType=policyDescription_description`
    - download: `/api/etf/pds/down/policyDescription/{fundCode}?type=description&token={token}`
  - Tokens expire quickly. Download immediately after token issuance.

- **KODEX/Samsung**
  - Prospectus files may use fund IDs under `m.samsungfund.com/upload/invest/{fundId}-A.pdf`.
  - Do not guess the fund ID without confirming through product metadata, page source, or a successful PDF download.

- **HANARO**
  - Product pages may expose direct `_upload/public/fund-new/...pdf` links in HTML.

- **ACE**
  - Product pages may call an API such as `/api/funds/{fundCode}/documents` on `papi.aceetf.co.kr`.
  - The response can contain direct `downloadUrl` fields for `투자설명서`.
  - **Live Metadata & AUM**: `GET https://papi.aceetf.co.kr/api/funds/{fundCode}`
    - `nastAmt` 필드에서 **확정 순자산총액(AUM, 원 단위)**을 오차 없이 직접 추출 가능 (`aum_krw = float(data['nastAmt'])`).
  - **Live Holdings (PDF)**: `GET https://papi.aceetf.co.kr/api/funds/{fundCode}/pdf?size=50`
    - KRX 공시 전 실시간/당일 비중(`wg`), 수량(`cu_ITEM_CNT`), 평가금액(`val_AM`), 종목코드(`jm_KSC_CD`), 종목명(`sec_NM`)을 즉시 조회 가능.
  - **주의**: 거래소 단축코드(예: `469150`)가 아닌 운용사 내부 펀드코드(예: `K55101E67600`)로 조회해야 함. 펀드코드는 상품 페이지 URL이나 메인 리스트 API(`https://papi.aceetf.co.kr/api/funds`)에서 역산 매핑.

- **TIGER/Mirae Asset**
  - Product pages often include direct `/tigeretf/upload/etf/...pdf` links for prospectus documents.
  - Strip session IDs from URLs when possible and test the clean URL.

- **KRX methodology**
  - `pypdf` extracts KRX methodology PDFs adequately. `Ignoring wrong pointing object` warnings are harmless. What breaks is **spacing**: table cells and clause numbers run together (`구성종목이5종목미만이면CAPLevel을적용하지않습니다`). Read with that in mind rather than assuming extraction failed. Fall back to rendered pages only if the text is genuinely garbled.
  - KRX sector methodology delegates heavily. The chain observed for KRX 섹터지수:
    - 심사대상종목·심사대상기간 → `KRX 규모별 TMI 방법론`
    - 유동주식비율·CAP·가중시점·구성종목 적격성 → `KRX 주가지수 기본 방법론`
    - 수시변경 → `KRX TMI 수시변경` + `KRX 기업이벤트적용 방법론`
    Record every hop in `종목선정관련_기타사항`, `비중산정관련_기타사항`, or `종목변경.in_out_주의사항`. Do not treat the sector PDF as self-contained.
  - For KRX sector indices, do not overclaim exact 수시변경 dates if the sector methodology only says to follow the basic methodology.
  - Clauses in `KRX 주가지수 기본 방법론` that materially change a rebalance estimate and are easy to miss:

    | 조항 | 내용 | 놓치면 생기는 오차 |
    |---|---|---|
    | 6.1 | 유동주식비율은 **1% 단위 올림** | 종목당 최대 1%p 비중 오차 |
    | 6.3.1 | 유동비율 정기변경은 **6월·12월 연 2회**, 신규-직전 차이 5% 미만이면 직전비율 유지 | 9월 리밸런싱에 적용되는 값은 6월 확정분. 조회 시점 값을 쓰면 기준일 불일치 |
    | 7.2 | 지수편입비중은 **정기변경월의 직전 3개월** 일평균시가총액 기준 | 심사기간(전전월 기준 3개월)과 다른 구간 |
    | 7.4 | CAP Factor는 정기변경일부터 다음 정기변경일 전일까지 **고정** | 적용일 비중이 CAP Level에 딱 떨어지지 않음 |
    | 9.1 / 9.2.1 | 지수는 **비교시점(실시간)** 유동시가총액으로 가중 | 평균 시총으로 목표비중을 내면 적용일 실제와 어긋남 |
    | 8.1 / 8.2 | 보통주만. 거래재개 후 30매매거래일 미경과 종목 제외 가능 | 편입 적격성 오판 |

**Download Validation**

After each download:

- Verify the file exists.
- Verify the first bytes are `%PDF-`.
- If the header is not `%PDF-`, inspect the file. It is often an HTML error, login page, or anti-hotlink response.
- Do not add the document to `ETF_info0.json` until the PDF is valid.

Common validation traps:

- HTTP 200 does not mean the body is a PDF.
- A saved file can be an HTML error page with `.pdf` extension.
- Korean filenames and `+`, `&`, spaces, parentheses in methodology filenames may require URL escaping.
- Some servers require `User-Agent` and `Referer` headers.
- Tokenized links can return 403 if requested without the token, after expiry, or without a browser-like referer.
- **A valid PDF can still be the wrong document.** Observed in this project: `docs/TIGER 반도체_지수방법론.pdf` was byte-identical (md5 `ca2e4685…`) to `TIGER 200 IT`, `TIGER 200IT레버리지`, and a file already flagged `KODEX 반도체_지수방법론.misfiled_*`, and its actual content was `KRX 반도체TR 레버리지 지수 방법론`. Four filenames, one document, none of them correct for the ETF. **Always open the PDF and confirm the index name on the cover matches `기초지수명`.**
- Run an md5 dedup pass over `docs/` after downloading. Identical hashes across different ETFs are legitimate only when the ETFs genuinely share one index — verify, do not assume.

**Identify The Underlying Index**

For each ETF, determine:

- ETF name
- ticker
- market cap or net assets, if user supplied or readily available
- issuer
- underlying index name
- index provider
- prospectus filename
- methodology filename

Use the prospectus, product page, or issuer fund metadata to confirm the underlying index. Do not infer only from the ETF name when the product page is available.

Important: multiple ETFs can use the same methodology file, and similar ETF names can use different indices. Reuse the same methodology PDF under ETF-specific filenames only after confirming the same underlying index.

**Read The Methodology**

Use PDF text extraction for first pass. If text extraction is broken, render pages or use screenshots for the relevant pages.

Extract information focused on reconstructing future holdings and weights:

- index overview
- universe rules
- constituent count
- regular rebalance schedule
- selection date
- weight fixing date
- effective date
- occasional/special rebalance rules
- constituent inclusion rules
- constituent exclusion rules
- buffer rules
- new listing rules
- merger/delisting/management issue rules
- weighting method
- fixed weights
- cap levels
- trigger thresholds
- post-adjustment cap levels
- excess weight redistribution method
- required external data
- important exceptions or committee discretion

When reading, separate three layers:

1. **Calendar rules**: when selection, weight fixing, and effective changes happen.
2. **Constituent rules**: which stocks enter or leave, including buffers and special events.
3. **Weight rules**: how weights are computed, capped, fixed, and redistributed.

Do not collapse these into one prose paragraph if the JSON is meant to support later calculation.

**JSON Schema**

Keep existing top-level fields and add `지수방법론`.

Use this structure where possible. Fields may be `null` or empty arrays if not available, but preserve the keys for consistency.

```json
{
  "번호": 1,
  "이름": "ETF name",
  "티커": "000000",
  "시가총액": "12,345억",
  "투자설명서파일명": "ETF name_투자설명서.pdf",
  "지수방법론파일명": "ETF name_지수방법론.pdf",
  "지수방법론": {
    "기초지수명": "",
    "산출기관": "",
    "방법론개요": "",
    "구성종목수": {
      "목표": null,
      "최소": null,
      "최대": null,
      "비고": ""
    },
    "유니버스": {
      "시장": "",
      "포함조건": [],
      "제외조건": [],
      "필요데이터": []
    },
    "종목선정": {
      "정기선정기준": [],
      "편입순서": [],
      "버퍼룰": null,
      "종목선정관련_기타사항": ""
    },
    "리밸런싱": {
      "정기": {
        "주기": "",
        "종목선정일": "",
        "비중확정일": "",
        "변경적용일": ""
      },
      "수시": [
        {
          "유형": "",
          "조건": "",
          "비중확정일": "",
          "변경적용일": "",
          "종목변경여부": ""
        }
      ]
    },
    "비중산정": {
      "기본방식": "",
      "고정비중": [],
      "개별상한": {
        "정기": null,
        "수시트리거": null,
        "수시조정후": null
      },
      "초과분처리": "",
      "비중산정관련_기타사항": ""
    },
    "종목변경": {
      "정기변경": "",
      "수시편입": null,
      "수시편출": null,
      "in_out_주의사항": ""
    },
    "추정": {
      "필요데이터": [],
      "가격만으로가능한것": "",
      "가격만으로어려운것": "",
      "추정난이도": ""
    }
  }
}
```

Use extended cap keys when a simple single cap is misleading, for example:

```json
"개별상한": {
  "정기_TOP2": 0.25,
  "정기_기타": 0.15,
  "수시트리거": 0.30,
  "수시조정후": 0.25
}
```

**Methodology Notes**

Always include:

- `종목선정관련_기타사항`
- `비중산정관련_기타사항`

Use these fields for committee discretion, industry relevance overrides, text-mining limitations, special inclusion/exclusion rules, missing linked methodology dependencies, or other material rules that do not fit cleanly in structured fields.

Be explicit about estimation limits:

- If price-only reconstruction is insufficient, say so in `추정.가격만으로어려운것`.
- If the methodology needs non-price data such as FICS/GICS classification, market cap, free-float ratio, trading value, sales data, text-mining scores, or index membership, list them in `추정.필요데이터`.
- If the index committee can override selections, preserve that in `종목선정관련_기타사항`.
- If a cap has different regular and special-rebalance levels, store both. Example: regular cap 20%, special trigger 30%, post-adjustment 25%.
- If top constituents have fixed weights, do not represent that as a simple cap only. Use `고정비중`.

**Editing Rules**

- Preserve existing ETF entries unless overwriting was confirmed.
- Preserve existing filenames if the same ETF is already present and the user confirms update, unless the user asks for new names.
- Assign `번호` sequentially after existing entries for new ETFs.
- Use valid JSON, no comments.
- The skill instructions may be written in English, but `ETF_info0.json` output must be in Korean by default.
- Use Korean field names to match the existing file.
- Write JSON string values in Korean when the source meaning can be expressed naturally in Korean. Keep official English index names, provider names, formulas, ticker symbols, and technical acronyms as-is when needed.
- Keep summaries concise but specific enough to implement a future calculation.

When updating JSON:

- Keep the file valid JSON only. No comments or trailing commas.
- Avoid storing absolute paths in JSON; store filenames only, because files live under `docs/`.
- Keep ticker strings as strings. Korean ETF tickers may contain letters, for example `0167A0`.
- For duplicate index methodologies, copy the methodology object per ETF rather than linking implicitly, unless the project already has a normalized schema.
- If market cap was user-supplied, preserve it. If fetched from the web, note uncertainty in final response if the source/date may matter.

**Final Verification**

Before finishing:

1. Parse `ETF_info0.json`.
2. Confirm every referenced PDF exists under `docs/`.
3. Confirm every referenced PDF starts with `%PDF-`.
4. **Confirm the index name printed on the PDF cover matches `기초지수명`.** A valid PDF of the wrong index is the most common silent failure.
5. **Run an md5 dedup pass over `docs/`.** Investigate every duplicate hash.
6. Confirm every new or updated ETF has `지수방법론`.
7. Confirm `종목선정관련_기타사항` and `비중산정관련_기타사항` exist.
8. Report any missing source, inaccessible document, or methodology dependency that could affect future reconstruction.

Useful PowerShell checks:

```powershell
$info = Get-Content -Raw .\ETF_info0.json | ConvertFrom-Json
$info.Count
foreach ($row in $info) {
  foreach ($field in @('투자설명서파일명', '지수방법론파일명')) {
    $path = Join-Path .\docs $row.$field
    if (-not (Test-Path -LiteralPath $path)) { Write-Host "missing $path" }
  }
}
```

PDF header check:

```powershell
Get-ChildItem .\docs -Filter '*.pdf' | ForEach-Object {
  $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
  $head = [System.Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(5, $bytes.Length))
  [pscustomobject]@{ Name=$_.Name; Header=$head; Length=$_.Length }
}
```

Duplicate-document check (catches misfiled methodology PDFs):

```powershell
Get-ChildItem .\docs -Filter '*.pdf' |
  Get-FileHash -Algorithm MD5 |
  Group-Object Hash |
  Where-Object Count -gt 1 |
  ForEach-Object { $_.Group.Path -join ' | ' }
```

---

## 3. ETF PDF·NAV·시장데이터 해석과 수집

이 장에서는 공시 PDF와 NAV를 어떻게 시간축에 맞춰 해석하는지, 실제 보유수량과 신고 정합성을 어떻게 검증하는지, 시장데이터를 어떤 우선순위와 품질 규율로 확보하는지를 다룬다. **시점 정렬·단위·기업행위 보정이 먼저이고, API 선택은 그 다음**이다.

특정 ETF에 국한되지 않는 일반 지식이며, 2026-09 세션에서 실측 검증했다.

| 검증 범위 | 대상 | 기간 |
|---|---|---|
| A~F (PDF·NAV 정합성, 데이터 소스) | KODEX 반도체(091160), TIGER 반도체(091230), KODEX 로봇액티브(445290), TIME Korea플러스배당액티브(441800) | 2026-07-01 ~ 09-10 |
| **G (지수 규칙 역산·검증)**, C5·C9a~c 보강 | ACE AI반도체TOP3+(469150) 및 FnGuide 계열 반도체 ETF 4종 | 정기변경 4회분(2025-09 ~ 2026-06), 후보 274종목 · 84,462행 |

A~F는 **KRX 산출 지수 + 패시브/액티브 ETF**에서, G는 **FnGuide 산출 지수 + 분기 정기변경**에서 얻었다. 산출기관이 다르면 접근 가능한 화면이 달라지므로(C5 적용 범위 박스) 어느 계열에서 검증된 지식인지 확인하고 쓴다.

> **단위 경고:** 이 프로젝트에서 반복적으로 발생한 실수 1위는 거래대금·시가총액의 단위 오류다. 출처마다 단위가 원 / 백만원 / 억원으로 제각각이고, 100배·1억배 틀린 결과도 그럴듯하게 보인다. 모든 금액 코드에 단위 접미사를 붙이고, 1장의 `C8. 단위` 규율을 먼저 적용한다.

**3.1 PDF 공시 구조**

**A1. PDF(t)의 수량은 t−1 종가 시점의 실제 잔고다**

평가가격은 조회 시각에 따라 움직인다 — 장 시작 전이면 t−1 종가, 장중이면 실시간, 정산 후면
t 종가. **수량만 t−1로 고정**이다. 따라서 오늘 올라온 PDF로 어제 NAV를 정확히 재현할 수 있다.

```text
NAV(t−1) × K = Σᵢ q_pdf,ᵢ(t) · pxᵢ(t−1) + 현금라인(t)
```

실측: 9/10 게시 PDF로 9/9 확정 NAV 재현 시 오차 **0.00bp**(두 ETF 모두, 5.85조 펀드에서 18만원).
같은 계산을 9/9 게시 PDF로 하면 −4.42bp / −2.64bp로 어긋난다.

**따라서 PDF에서 읽은 수량 변경은 게시일 하루 전에 체결된 것으로 귀속해야 한다.**
그리고 실시간 관측에는 **구조적으로 하루치 정보 공백**이 있다. 오늘 종가 매매는 내일 PDF에서만 보인다.

**A2. 원화현금 라인은 실제 현금이 아니라 플러그다**

정의상 `현금(t) = NAV(t−1)·K − Σ q_pdf(t)·px(t−1)`.

그래서 **A1 항등식을 그대로 검증하면 순환논리**가 된다. 반드시 0이 나오고 아무것도 증명하지 못한다.
운용사가 수량을 틀리게 신고해도 플러그가 그 차이를 흡수해 똑같이 0이 나온다.

> 플러그가 있는 데이터에서 정합성을 검증하려면 **플러그가 풀리지 않은 축**(다음 날 가격)을 써야 한다.

플러그는 음수가 될 수 있다(미지급금 성격). 값 자체가 정보를 담는 경우는 A5의 누락·오기뿐이다.

**A3. Σ평가금액 ÷ NAV = CU당 좌수(K)**

공시되지 않는 K를 이렇게 역산할 수 있고 보통 라운드 넘버로 떨어진다
(관측: 50,000 / 20,000 / 50,000 / 20,002).

**A4. 설정·환매는 CU당 수량과 1좌당 NAV를 바꾸지 않는다**

상장좌수만 바뀐다. 1좌 기준 분석에서는 무시해도 되지만 B3의 슬리피지는 예외다.

**A5. 거래정지 종목은 PDF 라인에서 통째로 빠질 수 있다**

그 가치는 플러그로 들어간다. 재개일에 라인이 복귀하면서 플러그가 그 비중만큼 점프한다.
실측: 코미코가 정지기간(2026-07-29~08-20) 동안 두 ETF PDF에서 사라졌고 플러그에 약 49bp가 들어가 있었다.

**플러그가 실제로 정보를 담는 거의 유일한 경우가 이 누락·오기다.**

**A6. PDF에는 종목코드가 없고 종목명만 있다**

동명이인·상호변경 위험이 있어 매핑을 반드시 검증해야 한다.
검증법: `PDF 평가금액 ÷ 수량`과 후보 종목코드의 그날 종가를 대조한다.

**3.2 신고 정합성 검증 방법론**

**B1. pseudo NAV 수익률**

현금항을 소거하면 정보가 산다.

```text
pseudo 수익률(t) = Σᵢ q_pdf,ᵢ(t) · Δpxᵢ(t) ÷ (NAV(t−1)·K)
실제   수익률(t) = NAV(t) / NAV(t−1) − 1
GAP(t)          = 실제 − pseudo          [bp]
```

t일에 매매가 없었다면 펀드는 하루 종일 그 수량을 들고 있었으므로 GAP = 0이어야 한다.

**정렬이 핵심이다.** PDF(t−1)을 쓰면 t−2 잔고라 이틀치 매매가 섞인다. PDF(t)를 써야 t일 매매만 분리된다.

**B2. 신호는 체결일에 안 보이고 그 뒤에 자란다**

```text
체결일       : GAP = Σ Δq·(종가 − 체결가)      ← 종가 단일가 체결이면 정확히 0
그 다음날부터 : GAP = Σ Δq·Δpx(t)   매일 발생
누적         : Σ Δq·[px(T) − px(t₀)]          ← 계속 커짐
```

**리밸런싱 직전 며칠의 선매매는 원리적으로 잡기 어렵고, 몇 주 전부터의 선매매는 잘 잡힌다.**
실측 검출 한계: 2거래일 경과 시 필요매매액의 19%, 3주 경과 시 2.7%.

**B3. ±몇 bp의 일상 노이즈는 매매가 없어도 정상이다**

설정·환매가 있으면 바스켓 전종목을 매수·매도해야 하고 그 종가 대비 슬리피지가 펀드에 계상된다.
부호가 매번 랜덤이라 **회전율과 GAP의 선형상관은 0**으로 나온다 — 회전율은 GAP의 *분산*과
관계있지 평균과는 무관하다. 상관계수로 검정하면 잘못된 결론이 난다.

관측 노이즈(GAP 표준편차): 패시브 9~10bp, 소형 액티브 15.8bp, 매매 없는 액티브 3.3bp.
**AUM이 작을수록, 설정·환매가 많을수록 커진다.**

**B4. 미신고 매매는 이상치가 아니라 드리프트로 나타난다**

신고 수량이 계속 틀린 채 있으면 매일 왜곡이 쌓인다. 단일일 z검정이 아니라 셋을 함께 본다.

```text
드리프트 t검정  : |t| > 2 이면 한쪽 편향
누적 / 랜덤워크 : 누적GAP ÷ (σ√n) > 1.5 이면 방향성 축적
부호 런 검정    : 런이 기대(1 + 2·n₊·n₋/n)보다 크게 적으면 같은 부호 지속
```

세 검정이 엇갈리면(예: 드리프트 t는 유의한데 런은 지속성 없음) **국지적 구간 효과**를 의심하고
기간을 쪼개 본다.

**B5. 종목별 수량 역추적은 원리상 가능하나 실무상 불가능하다**

"A종목만 움직였다면 A의 실제 수량을 역산"은 정확한 논리다. 그러나 같은 섹터 종목은 함께 움직인다.

실측: 35종목 일별수익률 평균 상관 0.533, 1주성분 설명력 56.3%, 차분 12개 vs 미지수 35개.
"지배 종목"의 지배비중은 18~51%로 90%를 넘는 날이 없었다.

한 종목만 미지수로 두면 **전체 편의가 그 종목에 몰려 비중 작은 종목일수록 배율이 폭발**한다
(실측 1.03~5.3배, 전부 인공물). 미지수를 그룹 단위(3~4개)로 줄여야 식별된다.

> **전 종목의 결과가 한쪽으로 쏠리면 방법이 틀린 것이다.**

**B6. 운용보수는 GAP에 상수 음수로 나타난다**

매매도 플로우도 없는 구간에서 GAP이 −0.07 ~ −0.11bp 같은 상수로 고정되면 그게 일일 보수 계상이다.
역으로 이 값에서 실효 보수율을 역산할 수 있다(0.1bp/일 ≈ 연 0.25%).

**B7. 두 개 이상의 독립 주체에서 같은 신호가 나오면 개별 요인이 아니다**

서로 다른 운용사의 GAP 상관이 0.89~0.95로 나오면 펀드 행위가 아니라 **보유 종목의 공통 이벤트**
(배당 기산, 권리락 등)다. 이 판별법이 오탐을 크게 줄인다.

**B8. 정직한 신고의 신호**

```text
당일 GAP 은 튀는데, 당일 PDF 기준으로 보면 정합  → 매매하고 바로 신고함
당일 GAP 이 튀고,  그 뒤로도 계속 어긋남         → 매매하고 신고 안 함
```

**3.3 데이터 의미와 정합성 함정**

**C1. pykrx는 수정주가, KRX PDF는 실거래가**

pykrx는 분할·무상증자를 **소급 조정**하고 KRX PDF는 당시 실제 거래가격을 쓴다.
섞으면 분할 종목에서 반드시 깨진다.

탐지법: `PDF 평가금액÷수량 ÷ pykrx 종가`가 1이 아니면 그 종목에 기업행위가 있고 그 배율이 조정 계수다.
실측 배율은 전 기간 정확히 일정하게 나온다(코미코 2.495, 한화 1.2005).
**배율이 특정일에 계단식으로 변하면 분할류가 아니라 실제 주식수 변동**(유상증자·소각·전환)이다.

파생 규칙: 심사기간 시가총액·ADV는 **분할 전 기간에 분할 전 주식수와 분할 전 가격**을 써야 한다.
둘 중 하나만 바꾸면 시가총액이 배율만큼 틀린다.

**단, 과거 시가총액을 `pykrx 종가 × 현재 상장주식수`로 재구성할 때는 분할류에 한해 오차가 상쇄된다.**

```text
분할·무상증자(배율 f) : (원주가/f) × (구주식수 × f) = 원주가 × 구주식수   → 정확 ✅
유상증자·자사주 소각    : 주식수만 변하고 가격은 비례조정되지 않음        → 그대로 틀림 ❌
합병·분할상장·전환     :                                              → 그대로 틀림 ❌
```

CLAUDE.md §1.3이 이 재구성 방식을 금지하는 이유가 뒤 두 줄이다. **분할류라서 괜찮은 경우와
실제 주식수 변동이라 틀리는 경우를 배율의 시간 형태로 갈라내면**, 금지 규칙을 지키면서도
같은 기간 KRX 시가총액을 못 받을 때 실용적으로 쓸 수 있다. 다만 결과에는 반드시 `대체` 등급을 남긴다.

**C2. 기업행위와 매매를 구분하는 법**

수량이 바뀌었을 때:

```text
기업행위 : 가격 대폭 점프(±15% 초과) + 수량비율 × 가격비율 ≈ 1 (가치중립)
매매     : 가격은 정상 범위, 수량만 변동
상한가   : 가격 ±30% 점프인데 수량비율 = 1.0000
```

**"가치중립"만으로 판정하면 안 된다.** 편출 −10% 매매가 주가 +5% 날과 겹치면 가치비율 0.95로
걸려 오탐한다(실측: 이 오탐으로 노이즈가 9→14bp로 악화). 반드시 **가격 점프 조건을 먼저** 걸고
pykrx 등락률과 대조해 확정한다.

- pykrx 등락률과 PDF 가격비율이 **일치** → 진짜 시세 변동
- pykrx는 소폭인데 PDF는 대폭 점프 → **기업행위**(pykrx가 소급조정한 것)

기업행위일의 pseudo 기여는 가치차 형태로 바꾼다.

```text
일반     : 기여 = q(t) · [px(t) − px(t−1)]
기업행위 : 기여 = q(t)·px(t) − q(t−1)·px(t−1)
```

미보정 시 실측 오차 **+136bp**(뉴로메카 무상증자 ×1.5).

**C3. PDF 평가금액은 조회 시각에 따라 달라진다**

수량은 안 변한다. 장중 스냅샷과 확정 NAV를 섞으면 **수십 bp 인공물**이 생긴다(실측 −43bp).
과거 확정일은 안전하고 당일 장중만 위험하다. 당일을 봐야 하면 시세와 NAV를 **동일 시점에 연달아**
받아야 한다(그러면 0.4bp로 수렴).

두 ETF에서 같은 크기의 오차가 동시에 나오면 이 문제를 먼저 의심한다.

**C4. 거래량 0인 거래정지일을 ADV 평균에 넣으면 안 된다**

정지일을 제외하고 실제 거래일 수를 기록한다. 실측: 정지 8일 포함 시 ADV가 1.6배 과소계상됐다.

**C5. 지수반영주식수 ÷ 상장주식수 = 공식 유동주식비율**

지수 구성종목 자료에 지수반영주식수가 있으면 이렇게 공식 유동비율을 역산할 수 있다.
**1% 단위 정수로 떨어지는지가 검증**이다(기본방법론 6.1의 1% 올림).

- CAP 적용 종목은 CAP Factor가 섞여 있어 역산 불가
- 외부 추정치(WiseReport 등)와 최대 10%p까지 차이가 날 수 있음
- 역산값이 100%를 넘으면 **상장주식수 쪽이 틀린 것**(분할 미반영 등)

이렇게 얻은 값은 `official_float` 등급으로 승격할 수 있다.

> #### ⚠️ 적용 범위 — KRX 산출 지수를 추종하는 ETF에서만 된다
>
> 030303(지수구성종목) 화면은 **KRX가 산출하는 지수를 추종하는 ETF에만 행을 돌려준다.**
> FnGuide·에프앤가이드 계열 지수를 추종하는 ETF는 HTTP 200에 **0행**이 온다(에러가 아니라 빈 응답이라 조용히 실패한다).
>
> | ETF | 기초지수 산출기관 | 030303 결과 |
> |---|---|---|
> | KODEX 반도체 (091160) | KRX | 35행 |
> | ACE AI반도체TOP3+ (469150) | FnGuide | **0행** |
> | HANARO Fn K-반도체 (395270) | FnGuide | **0행** |
> | SOL AI반도체소부장 (455850) | FnGuide | **0행** |
> | TIGER 반도체TOP10 (396500) | FnGuide | **0행** |
>
> 2개 기준일(2026-09-09, 09-10)에서 동일했다.
> 하필 **FnGuide 유동비율이 필요한 지수에서만 막힌다.** FnGuide 방법론이 "FnGuide 유동주식비율"을 지정하는 경우
> 이 경로로는 확보할 수 없으므로 `추정`(WiseReport) 또는 `미확인`으로 남긴다.
> KRX 유동비율을 대신 쓰는 것은 산출기관이 다른 값이므로 `proxy` 등급이다.
>
> 💡 **유동비율 대체값 및 최후의 폴백(Fallback) 주의사항:**
> - 네이버 외인소진율을 유동비율로 사용하는 것은 절대 금지한다.
> - SEIBRO의 `주식분포현황(결산기준)`(`BIP_CNTS01047V`)에서 최대주주/소액주주 지분을 역산해 유동비율을 구하는 방식은 연 1회/반기 결산 시점 데이터라 시점 불일치가 크고, 자사주/보호예수/비유동 블록 계산 복잡도로 인해 **1차 데이터 소스로 사용하는 것을 엄격히 금지**하며, 다른 모든 경로(`official_float`, WiseReport `추정`)가 막혔을 때의 **최후의 폴백(Fallback)**으로만 제한적으로 검토한다.

> `C8. 단위` 규칙은 전 프로젝트 공통이므로 1장에 canonical하게 배치했다.

**3.4 데이터 확보 우선순위와 공식·우회 경로**

**C10. KRX OpenAPI — 유일한 공식 거래대금·시가총액 경로**

```text
호스트 : data-dbg.krx.co.kr
인증   : API Key (프로젝트에서는 token.env 의 KRX_API_KEY)
실패예 : {"respMsg":"Unauthorized Key","respCode":"401"}
         → 키가 틀린 게 아니라 미승인 상태라는 뜻. 발급처에서 승인 절차를 밟아야 한다.
```

이 경로가 열리면 **거래대금 대체계산과 시가총액 재구성이 동시에 공식 등급으로 올라간다.**
현재 남아 있는 데이터 품질 결손 중 가장 큰 두 개다. 우회로를 찾는 것보다 키 승인을 뚫는 편이 싸다.

`data.krx.co.kr`(정보데이터시스템 웹)과는 다른 호스트다. 웹 쪽은 C6대로 세션 검증으로 막힌다.

**C6. KRX 정보데이터시스템은 봇 차단, 모바일 웹은 열려 있다**

`data.krx.co.kr`은 SSL이 아니라 **세션 검증**으로 막힌다. 로더 페이지로 쿠키를 받아도
`getJsonData.cmd`가 HTTP 400 `LOGOUT`을 반환한다. 그래서 pykrx의 KRX 백엔드 함수
(`get_market_cap`, `get_etf_ohlcv_by_date`, 티커 목록 등)가 빈 결과나 KeyError로 실패한다.
`get_market_ohlcv`는 네이버 백엔드라 정상 동작한다.

`m.krx.co.kr` 모바일 그리드는 열려 있다.

```text
se_key 발급 : GET  /contents/COM/JHPETPCM_KEY.jspx
조회        : GET  /inc/lib/mobilegrid/mobilegrid.jsp
파라미터    : mkt=ETF, se_key, isu_cd(ISIN), domforn=00, uly_gubun=00, gubun=00,
             bldPath=..., 그리고 date= 또는 fromdate=/todate=
Referer     : /contents/03/0303/{메뉴}/JHPETP{메뉴}M01.jsp  필요
```

| bldPath | 화면 | 반환 열 |
|---|---|---|
| `/03/0303/030301/hpetp030301m02` | 설정·환매 | 일자, 설정, 환매, **발행수익증권수(상장좌수)**, 전일 |
| `/03/0303/030302/hpetp030302m01` | PDF | 종목명, CU당 수량, (기준가), **평가금액**, 구성비중 |
| `/03/0303/030303/new/hpetp030303m01` | 지수구성종목 | 종목명, **지수반영주식수**, 유동시가총액, 구성비 |
| `/03/0303/030304/new/hpetp030304m01` | 추적오차 추이 | 일자, 순자산가치, 기초지수, **추적오차율** |
| `/03/0303/030305/hpetp030305m01` | 괴리율 추이 | 일자, ETF종가, **순자산가치(NAV)**, 괴리율 |

ETF ISIN은 종목코드에서 계산한다: `KR7` + 6자리코드 + `00` + ISIN 체크디짓(Luhn).

체크디짓은 **문자를 숫자로 확장(A=10 … Z=35)한 뒤 Luhn**이다. 문자가 섞인 신형 티커도 그대로 동작한다.

```python
def isin_of(code):                       # '091160' -> 'KR7091160002'
    b = 'KR7' + code + '00'
    s = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in b)
    tot = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9: d -= 9
        tot += d
    return b + str((10 - tot % 10) % 10)
```

**알려진 ISIN 두 개 이상으로 먼저 검증한 뒤 미지 종목에 적용한다.**
검증 예: `091160 → KR7091160002`, `091230 → KR7091230003`, 문자 포함 `0167A0 → KR70167A0001`.
검증 없이 쓰면 틀린 ISIN이 0행을 돌려주는데, 위 C5 박스의 "지수 미지원 0행"과 **구분이 안 된다.**

**C6a. SEIBRO (한국예탁결제원) ETF 직접 데이터 경로 (`BIP_CNTS06*`)**

한국예탁결제원 증권정보포털 SEIBRO(`https://seibro.or.kr/`)는 운용사 공시 및 거래소(`m.krx`) 외에 **예탁원 결제 원장 기준의 ETF 공식 데이터**를 제공하는 매우 유용한 1차/보조 원천이다.

| SEIBRO 화면 ID | 메뉴명 | 반환 항목 및 분석 활용 가치 |
|---|---|---|
| `BIP_CNTS06036V` | **종목보유현황** | • 예탁원 결제 기준 **ETF 편입 전종목 및 수량**.<br>• 운용사 웹/KRX PDF 공시 수량과 일치 여부를 대조하는 **독립 교차 검증 소스**. |
| `BIP_CNTS06026V` | **종목별 설정/환매현황** | • 일자별 **설정/환매 CU(Creation Unit) 증감 수량 및 금액**.<br>• 리밸런싱 직전/직후 기관·LP 자금 유출입 추적 (A4/B3 슬리피지 및 선행 수급 파악). |
| `BIP_CNTS06025V` | **종목발행현황** | • 전 ETF 마스터 정보 (티커, ISIN, 기초지수명, 상장일, 펀드 형태, 총발행증권수). |
| `BIP_CNTS06033V` | **기준가추이** | • 일자별 확정 NAV, 전일대비, 괴리율 추이. |
| `BIP_CNTS06030V` | **분배금지급현황** | • 과거 분배금 지급 내역 및 분배락 기준일 정보. |

> **활용 팁**: WebSquare 기반 시스템(`proworks/callServletService.jsp`)이므로, `m.krx` 화면에서 특정 일자의 PDF나 설정환매 데이터가 지연되거나 불일치할 때 SEIBRO의 `06036V`(보유현황) 및 `06026V`(설정환매)를 상호 대조(Cross-check)하면 데이터 무결성을 즉시 검증할 수 있다.

**C9. 네이버 계열 API 경로와 한계**

HTML 정규식은 종목 수가 늘면 반드시 깨진다. JSON API를 쓴다.

| 경로 | 반환 |
|---|---|
| `m.stock.naver.com/api/stock/{code}/price?pageSize=N&page=1` | 일별 종가·시고저·**거래량**·등락률 |
| `m.stock.naver.com/api/stock/{code}/basic` | **`tradeStopType`**, **`newlyListed`**, `tradableStatus` |
| `m.stock.naver.com/api/stock/{code}/integration` | 업종코드, 컨센서스, 종목명 |
| `m.stock.naver.com/api/stock/{code}/trend` | 투자자별 순매수 **수량**, 외국인보유비율 |
| `api.finance.naver.com/siseJson.naver?symbol=...&timeframe=day` | 날짜·시가·고가·저가·종가·**거래량**·외국인소진율 |
| `finance.naver.com/api/sise/etfItemList.nhn` | ETF 전종목 목록·NAV·`marketSum`(백만원) |
| `navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={code}` | 상장주식수, 유동비율, 시가총액(억원), **WICS** 업종 |
| `finance.naver.com/sise/sise_market_sum.naver?sosok=0\|1&page=N` | **주식 전종목** 현재가·시가총액(억원)·상장주식수(천주)·거래량 |
| `finance.naver.com/sise/sise_group.naver?type=upjong` | 업종 목록과 업종번호 |
| `finance.naver.com/sise/sise_group_detail.naver?type=upjong&no=N` | **해당 업종 전 구성종목** |

**네이버 계열에는 일별 거래대금 시계열이 없다.** 위 4개 시세 경로를 전부 확인했고 거래량만 제공한다.
따라서 거래대금 시계열은 KRX OpenAPI를 뚫거나 `종가 × 거래량` 대체계산뿐이다.

**C9a. 당일 누적 거래대금은 있다 — 대체계산 오차를 실측하는 데 쓴다**

`integration`의 `totalInfos` 안에 **`accumulatedTradingValue`(당일 누적 거래대금)** 가 있다(단위 문자열, `"4,179억"` 형태).
시계열이 아니라 시계열 대용은 안 되지만, 용도가 하나 있다 — **`종가 × 거래량` 대체계산의 오차를 실측하는 것.**

```python
ti  = {x['code']: x['value'] for x in j['totalInfos']}
real  = parse_krw(ti['accumulatedTradingValue'])          # 실제 거래대금
proxy = close_price * float(ti['accumulatedTradingVolume'].replace(',', ''))
err   = proxy / real - 1
```

> **반드시 장 마감 후에 측정한다.** 장중에 재면 C3의 시점 불일치가 섞여 오차를 크게 과대평가한다.
> 같은 종목을 같은 날 장중과 마감 후에 각각 잰 실측:
>
> | 종목 | 장중(13:40) | 마감 후 |
> |---|---|---|
> | 한미반도체 | +0.8% | −1.22% |
> | 주성엔지니어링 | **+3.8%** | −1.00% |
> | SK하이닉스 | −0.5% | −0.16% |
> | 심텍 | +1.1% | +0.11% |
>
> **마감 후 기준 진짜 오차는 ±1.3% 이내다.** 장중 측정치는 3배 이상 부풀려진다.

이 숫자가 있어야 **"결론이 대체계산 오차로 뒤집히는가"** 를 판정할 수 있다.
순위 경합이 걸린 두 종목의 스코어 격차가 이 오차 범위 안이면 결론을 낼 수 없고, 밖이면 대체계산이어도 결론이 선다.
보고서에는 오차 실측치를 함께 싣는다.

**C9b. 전종목 시총·상장주식수 벌크 경로**

`data.krx`가 막혔을 때(C6) 전종목 시가총액·상장주식수를 한 번에 받는 경로다.

```text
finance.naver.com/sise/sise_market_sum.naver?sosok=0(코스피)/1(코스닥)&page=1..15
→ 시장당 50종목 × 15페이지 = 750종목, 합 1,500종목
table.type_2 의 td 인덱스: [2]현재가 [6]시가총액(억원) [7]상장주식수(천주) [9]거래량
```

**현재 시점 스냅샷이라 시계열은 안 된다.** 용도는 두 가지다.

- **전종목 커버리지 확보** — 후보 유니버스를 만들 때 "빠진 대형주가 없다"를 보장한다
- **상장주식수 벌크 수집** — 종목당 1콜(wisereport)을 1,500종목 30콜로 줄인다

`시가총액(억원) ≈ 현재가 × 상장주식수(천주) × 1000 / 1e8` 자체 검산이 되므로 **C8 단위 검증을 겸한다.**
등급은 `현재값만`이다. 과거 심사기간 계산에 쓰면 기준일 불일치가 생긴다.

**C9c. 업종 벌크 경로와 종목별 교차검증**

C9 표의 wisereport는 종목당 1콜이다. 업종 전체를 두 콜로 받는 경로가 있다.

```text
sise_group.naver?type=upjong          → 업종번호 목록
sise_group_detail.naver?type=upjong&no=278   → 반도체와반도체장비 전 구성종목
                                     no=282   → 전자장비와기기 전 구성종목
```

그리고 `m.stock/integration`의 **`industryCode`가 같은 번호 체계**를 반환한다(한미반도체 → `278`).
**벌크로 받고 종목별로 대조하는 교차검증**이 성립한다. 실측: 274종목 분류를 2콜 + 종목별 확인으로 처리했다.

주의 — 이 분류는 여전히 **WICS 계열이고 FICS가 아니다.** 위 WICS ≠ FICS 규율이 그대로 적용된다.
`sise_group_detail`에는 **우선주가 섞여 나오므로** 종목명 `우`/`우B`/`N우` 패턴을 제거해야 한다.

`basic`의 `tradeStopType` / `newlyListed`는 **결측일 원인 분류**(거래정지 / 신규상장 전 / API 오류)에
쓸 수 있다. CLAUDE.md §1.3이 요구하는 구분을 이걸로 충족한다.

업종은 **WICS**이고 FnGuide 계열이라 FICS의 최선의 프록시지만 **WICS ≠ FICS**다.
방법론이 FICS 소분류를 요구하면 등급을 `proxy`로 두거나 `미확인`을 유지한다.
GICS를 요구하는 KRX 지수에 WICS를 대입하는 것도 같은 문제다.

**C7. 기업 프록시 SSL은 truststore로 해결한다**

```python
import truststore
truststore.inject_into_ssl()
```

Windows 시스템 인증서 저장소를 쓰므로 `verify=False`로 검증을 끌 필요가 없다.
`certificate verify failed: unable to get local issuer certificate`가 뜨면 이것부터 시도한다.

**3.5 데이터 수집 절차·보존물·위생 체크리스트**

두 갈래의 실제 수집 경험(35종목·2개월 정밀 추적 / 274종목·15개월 대량 수집)을 합친 것이다.

**F1. 수집 순서**

```text
1. 공식 API 먼저          KRX OpenAPI (C10). 키 문제라면 승인을 뚫는 게 우회보다 싸다.
2. 막히면 실패를 기록      "차단"이 아니라 "HTTP 400 LOGOUT / 세션검증"까지 정확히.
                          SSL 오류면 truststore 부터 (C7). verify=False 로 끄지 말 것.
3. JSON API 우회          m.krx 모바일 그리드 (C6), m.stock API (C9).
                          HTML 정규식은 최후 수단 — 종목 수가 늘면 반드시 깨진다.
4. 그래도 없으면 대체계산   반드시 등급을 붙이고 산식을 명시.
```

한 경로가 막혔다고 그 데이터를 포기하기 전에, **같은 데이터를 다른 축으로 주는 화면**이 있는지 본다.
예: 전종목 시가총액을 못 받아도 ETF 지수구성종목 화면(030303)에 유동시가총액이 종목별로 들어 있다.

**F2. 필수 산출물 4종**

수집 결과만 남기면 나중에 재현도 검증도 못 한다. 네 개를 함께 남긴다.

| 산출물 | 내용 | 왜 필요한가 |
|---|---|---|
| **막힌 경로 표** | 시도한 곳 · 정확한 에러 문자열 · **다운스트림 영향** | 다음 사람이 같은 벽에 다시 부딪히지 않는다. 보고서의 한계 서술이 여기서 바로 나온다 |
| **확보 데이터 표** | 필요 데이터 · 최종 출처 · 확보량 · **등급** | 어떤 결론이 어느 등급 위에 서 있는지 추적된다 |
| **source_manifest** | URL · HTTP · 바이트 · sha256 · 파싱행수 · **조회시각** | 조회시각이 없으면 장중본과 확정본을 사후에 구분할 수 없다 |
| **원자료 보존** | `holdings_raw/{asof}_*.html` 원본 그대로 | 파싱 로직이 바뀌어도 재파싱 가능. 같은 날을 여러 시각에 받아 비교할 수 있다 |

뒤 둘의 값어치는 실제로 증명됐다. 같은 PDF를 세 시각에 받아 비교해서 "장중 실시간본 vs 확정본"을
갈라냈고, 그게 아니었으면 −43bp 인공물을 진짜 신호로 착각할 뻔했다 (C3).

**F4. 데이터 위생 체크리스트**

```text
□ 단위 검산               Σ(PDF 평가금액) ÷ NAV 가 라운드 넘버인가 (C8)
□ 금액 변수 접미사        _krw / _eok / _jo 없는 금액 변수가 없는가 (C8)
□ 수정주가 여부           배율 = PDF내재가 ÷ pykrx종가 가 1.0000 인가 (C1)
□ 기업행위 전수 탐지      배율이 계단식으로 변하는 종목 = 실제 주식수 변동 (C1, C2)
□ 거래정지일 식별         tradeStopType 또는 거래량 0. ADV 평균에서 제외 (C4, C9)
□ 신규상장 식별           newlyListed. 심사기간 일부만 존재하는 종목
□ 조회시각 기록           장중 스냅샷과 확정값을 섞지 않았는가 (C3)
□ 기준일 컬럼화           상장주식수·유동비율의 기준일을 데이터에 박았는가
□ 결측 원인 분류          거래정지 / 상장 전 / API 오류 구분. 0으로 채우지 말 것
□ 종목명 → 코드 검증      가격 대조로 확인. PDF 에는 코드가 없다 (A6)
□ 동일 파일 중복 검사     docs/ md5 — 방법론 PDF 오배치 탐지 (1부 Download Validation)
□ 부분관측 표시           상위 10종목 자료를 전종목으로 쓰지 않았는가
□ 0행 응답 구분           HTTP 200 + 0행이 ISIN 오류인가 지수 미지원인가 (C5, C6)
□ 대체계산 오차 실측      종가×거래량 오차를 장 마감 후 측정했는가 (C9a)
□ 결론 vs 오차 범위       경합 종목 격차가 대체계산 오차 범위 밖인가 (C9a)
□ 위임 문서 확인          방법론이 부록·별도문서로 넘긴 항목을 끝까지 읽었는가 (G7)
```

**규칙을 재구성해 편입·편출을 추정하는 작업이면 G장의 검증을 추가로 통과해야 한다.**

```text
□ 정기변경 전후 PDF 쌍    최소 4회분 확보했는가 (G1)
□ 모호 문언 판별          후보를 재현율로 골랐는가, 판별 안 되는 자유도를 명시했는가 (G2, E2)
□ 구간별 재현율           결론이 놓인 구간의 재현율을 신뢰도로 제시했는가 (G3)
□ 기저율 대조             예측한 교체 종목 수가 과거 분포 안에 있는가 (G4)
□ 분모 배수 계산          Σ분자1/Σ분자2 를 계산했는가. 0.5:0.5로 착각하지 않았는가 (E3)
□ 대안가설 기각 기록      가설을 나열해 각각 검정하고 기각 사유를 남겼는가 (G6)
□ 재량 조항 확인          방법론의 재량 층을 읽고 구간별 신뢰도를 나눴는가 (E4)
□ 순환논증 검사           관측 불가 필터로 오차를 메우지 않았는가. 시점 간 안정성 검정 (E1)
□ 과거 편입 이력 전수     정량 자격에도 미편입 의심 종목은 과거 전수 스캔으로 구조적 사유 확인했는가 (G8)
```

**F7. 산출물이 수식이면 계산 엔진으로 재계산해 검증한다**

검산 가능한 엑셀을 만들어 넘길 때, openpyxl은 **수식 문자열을 쓰기만 하고 계산하지 않는다.**
저장 시점에는 `#REF!`·순환참조·잘못된 시트 참조가 있어도 알 수 없고, 사용자가 열어야 드러난다.

Excel COM으로 재계산해 검증한다.

```python
import win32com.client as win32
app = win32.gencache.EnsureDispatch('Excel.Application')
app.Visible = False; app.DisplayAlerts = False
wb = app.Workbooks.Open(ABS_PATH)
app.CalculateFullRebuild()
errs = [v for row in wb.Worksheets('계산').UsedRange.Value or []
          for v in (row or []) if isinstance(v, str) and v.startswith('#')]
# 계산값을 읽어 파이썬 결과와 대조한 뒤
wb.Close(SaveChanges=False); app.Quit()
```

**수식 오류 개수 0**과 **파이썬 계산값과의 일치**를 함께 확인한다. 이중 검산이 된다.
원자료 → 중간값 → 최종값을 전부 수식으로 연결하고 가정을 토글 셀로 빼두면,
받는 사람이 가정을 바꿔가며 직접 검증할 수 있다.

**3.6 운용사 리밸런싱 행태 — 관측 기반 경험칙**

관측 표본이 작으므로 경향으로만 취급한다.

**D1. 선행매매는 실제로 일어나지만 규모가 작다**

관측 사례에서 필요 매매액의 1~6% 수준이었고 **물량의 대부분은 리밸런싱 당일 종가에 남는다.**

**D2. 선행매매 방식이 두 갈래로 갈린다**

```text
유동성 트리아지형 : 시장충격비율 상위 종목만 골라 큰 비율로 처분
                   (실측: 편출 16종목 중 충격비율 1~5위만 −33%, 우연 확률 1/4,368)
바스켓 균등형     : 편출 전종목을 같은 비율로 며칠에 걸쳐 감축
                   (실측: 전종목 −10% → 추가 −15%, 누적 −23%)
```

**D3. 매수보다 매도를 먼저 한다**

관측된 선행매매는 편출 감축이 대부분이었고 신규편입 종목은 적용일까지 0으로 남아 있었다.

**D4. 종가 단일가 체결을 전제하면 안 된다**

장중 분할 체결 비중이 오히려 클 수 있다. 이건 B2의 검출력 계산을 바꾼다.
GAP을 역산하면 `GAP × NAV(t−1)·K = Σ Δq·(종가 − 체결가)`로 평균 체결가를 추정할 수 있다.

**D5. 같은 지수를 추종하는 패시브 ETF끼리는 비중이 거의 같다**

실측 평균 0.035%p 차이, 최대 0.54%p. 한쪽 PDF를 다른 쪽 대용으로 쓸 수 있다.
다만 **추적오차율은 두 배 가까이 차이 날 수 있다**(0.90% vs 1.66%).

**D6. "액티브"라는 이름이 실제 회전율을 보장하지 않는다**

PDF 수량 변경 빈도로 실질 회전율을 직접 셀 수 있다.
실측: 한 액티브 ETF는 49거래일 중 **6일**만 구성이 바뀌었다(사실상 패시브).
다른 액티브는 13일 변경 + 신규·삭제 라인 23건으로 실제 액티브였다.

**D7. 관측 범위에서 PDF 신고는 정직했다**

매매한 날은 예외 없이 다음날 PDF에 반영됐다. 패시브 2 + 액티브 2 모두
드리프트·누적·런 검정을 통과했다. 다만 검출 한계가 있으므로
"미신고가 없다"가 아니라 "**검출 한계 이상의 미신고는 없다**"로 표현해야 한다.


**3.7 지수 리밸런싱 검증 및 유니버스 보완 (G1, F6)**

**G1. 정기변경 전후 PDF를 쌍으로 받으면 편입·편출이 확정된다**

적용일이 D+2라면 **D+1일과 D+3일 PDF** 두 개면 된다(A1에 따라 수량이 T−1이므로
D+3일 PDF가 D+2 잔고 = 변경 후 구성이다). 두 집합의 차집합이 편입·편출이다.

```text
편입 = act(변경후) − act(변경직전)
편출 = act(변경직전) − act(변경후)
```

정기변경 4회분(약 1년)이면 검증에 충분하다. 실측: 11개 기준일 232행으로 4회 편입·편출 이력을 전부 복원했다.
**이 쌍이 없으면 아래 G2~G5가 전부 불가능하다.** 문서 수집 단계에서 반드시 함께 받아 둔다.

**F6. 유니버스는 동종 ETF 전종목 합집합으로 만든다**

방법론의 기초 유니버스 명단을 직접 받을 수 없을 때 가장 싸고 확실한 대안이다.
같은 테마를 추종하는 ETF 여러 개의 PDF 전종목을 모아 합집합을 만들면
`historical_observed_universe`(CLAUDE.md §1.5)가 바로 나온다.

과거 정기변경 전후 기준일까지 포함해 받으면 편입·편출 이력이 함께 잡힌다.
단, 이렇게 만든 유니버스는 **공식 심사대상종목 명단이 아니므로**
`검증 전 추정 유니버스`로 표시하고, 누락 가능성이 결론에 미치는 영향을 함께 적는다
(예: 누적 시가총액 커버리지 기준을 쓰는 지수는 분모가 달라져 결과가 뒤집힐 수 있다).


**3.8 FnGuide/FICS 테마지수 특수 규칙 (FG1, FG2)**

**FG1. FnGuide 테마 지수의 계층적 업종 분류(FICS)와 슬롯 배정 함정 (★ docs 원본 참조)**

> #### 🚨 [필독] FnGuide 지수 추종 ETF 분석 시 FICS 데이터 소스 규칙
> **FnGuide 지수를 사용하는 ETF들은 대부분 FICS(FnGuide Industry Classification Standard) 분류를 사용한다.**
> 과거에는 FICS 원본이 없어 WICS나 네이버 포털 업종을 대체재(`proxy_fics`)로 사용하여 오차가 발생했으나, **현재 `docs/` 폴더에 공식 FICS 엑셀 데이터베이스가 완비**되어 있다.
> - **코스피**: `docs/코스피 FICS업종분류.xlsx` (834개 전종목)
> - **코스닥**: `docs/코스닥 FICS업종분류.xlsx` (1,819개 전종목)
> - **포함 정보**: 종목코드(6자리), 종목명, 시가총액(억원), 대분류, 중분류, 소분류
>
> FnGuide 계열 지수의 유니버스 스크리닝(예: 반도체TOP10, AI반도체TOP3+, K-반도체, 2차전지 등)을 수행할 때는 **외부 웹 크롤링이나 불확실한 대체값을 쓰지 말고, 반드시 `docs/` 내의 이 FICS 원본 엑셀 파일들을 최우선 참조**하여 대/중/소분류를 정확히 매칭해야 한다.
>
> 💡 **폴백(Fallback) 안내**: 만약 시간이 경과하여 상장종목 변동 등으로 FICS 데이터를 새로 최신화하고 싶다면, 한국예탁결제원 증권정보포털 **SEIBRO (https://seibro.or.kr/)**에 접속하여 최신 FICS 업종 데이터를 다운로드받아 `docs/`에 업데이트하면 된다.

FnGuide의 많은 테마·전략 지수(`AI반도체 TOP3+`, `반도체 TOP10` 등)는 **유니버스 선정 단계와 상위 슬롯(고정비중) 배정 단계의 업종 기준이 서로 다르다.**

- **유니버스 선정**: 반도체(`FICS.45.30.10`)뿐 아니라 전자 장비 및 기기(`FICS.45.20.30`) 등 인접 업종까지 폭넓게 포괄.
- **상위 슬롯(TOP 3 각 25% 등) 배정**: 지수방법론 본문에 특정 소분류(예: *FICS 소분류 반도체 및 관련장비에 포함된 종목 중 상위 3종목*)로 **자격이 제한**됨.

> **놓치면 생기는 치명적 오차**:
> 삼성전기, LG이노텍, 대덕전자처럼 시가총액과 거래대금이 거대한 전자장비 종목은 재무 스코어가 3위 이내로 나와도 **규정상 TOP 3 슬롯에 들어갈 수 없고 잔여 동일가중(약 1.4%)으로 배정**된다. 
> 유니버스 통과 목록만 보고 단순 스코어 순으로 상위 슬롯을 배정하면 포트폴리오 비중이 25% vs 1.4%로 완전히 왜곡된다. `docs/*FICS업종분류.xlsx`의 **소분류 컬럼**을 반드시 조회하여 검증하라.

**FG2. FnGuide Appendix D '상장협 매출 필터'의 실체적 해석과 정성 재량**

- **오해**: "AI 반도체 매출 비중(%)이 높아야 유니버스에 남는다." ❌
- **실체**: **비중 기준이 아니라 '키워드 매출의 존재 유무(Yes/No)'** 필터다.
  - 방법론의 키워드 목록(`인쇄회로기판`, `PKG`, `반도체 제조용 장비`, `TEST SOCKET` 등)이 사실상 반도체 소부장 전반을 포괄하므로, 정상적인 반도체 기업은 매출 필터 자체로 결격되지 않는다.
- **하위권 종목 생존/탈락의 진짜 열쇠**:
  - Appendix D에는 *"상장협 매출 데이터의 한계를 보완하기 위해, 최종 선정된 기업들의 실제 산업 내 지위 등이 지수와 어긋나지 않는지 **운용사 및 애널리스트, 관련 업계 전문가의 의견을 반영**한다"*는 정성적 재량 조항이 명시되어 있다.
  - 파크시스템스처럼 스코어 20위 밖(23~27위)으로 밀려도 4회 연속 생존하는 기현상은 모델 오차가 아니라 **이 정성적 재량 층에서 부여된 산업 내 독점 지위 가점** 때문이다.
  - 따라서 하위권 종목 예측 시에는 단순 정량 컷오프 외에 **[정성 재량 방어 시나리오]**를 반드시 병행 표기해야 한다.


---

## 4. 부록: SEIBRO(증권정보포털) 심층 수급·오버행 참고 데이터

이 장은 한국예탁결제원 증권정보포털 **SEIBRO (`https://seibro.or.kr/`)**에서 조회 가능한 수급, 오버행, 권리 변동 등 보조 참고 데이터를 정리한다. 단순 정량 가격/거래량 계산을 넘어선 **선행 수급 감지, 락업 해제 충격, 기업 이벤트 추적**에 유용하게 참고할 수 있다.

> ⚠️ **원칙**: 이 데이터들은 심층 분석 및 정성적 참고용으로 활용하며, 공식 지수 계산의 1차 입력값으로 무단 대체하지 않는다.

### 4.1 오버행 & 유동비율 변동 추적 (의무보유등록·보호예수)
- **화면 ID**: `BIP_CNTS01045V` (의무보유등록 / 반환정보)
- **제공 데이터**: 종목별 의무보유등록(보호예수) 해제일, 등록사유(최대주주, 벤처금융, 우리사주 등), 해제 주식수 및 총발행 대비 비율.
- **활용 가치**:
  - 신규 상장 6개월~1년 차 종목이 대규모 락업 해제 시, **유동주식비율($FF_i$)이 계단식으로 급등**하여 다음 정기변경 심사 대상(시총/유동시총 커트라인)에 진입할 가능성을 수개월 전 사전 포착.
  - 리밸런싱 직전 대규모 물량 출회(오버행)로 인한 주가 왜곡 및 지수 탈락 가능성 평가.

### 4.2 자본변동 및 상장주식수 정합성 추적 (발행주식수 증감내역)
- **화면 ID**: `BIP_CNTS01012V` (발행주식수증감내역 - 개별)
- **제공 데이터**: 전환사채(CB)·신주인수권부사채(BW) 권리행사, 유상/무상증자, 감자, 주식소각, 합병 등에 따른 **일자별 실제 주식수 변동일과 원인**.
- **활용 가치**:
  - `C1. 배율의 계단식 변동` 발생 시 해당 종목의 기업행위 원인을 원장 수준에서 즉시 규명.
  - 심사 기준일(t) 시점의 실제 상장주식수를 과거 소급 조회하여 기준일 불일치 오류 방지.

### 4.3 공매도 & 헷지 수급 추적 (대차거래 및 대차잔고)
- **화면 ID**: `BIP_CNTS08003V` (종목별 대차거래현황), `BIP_CNTS08007V` (내외국인 대차잔고 비교)
- **제공 데이터**: 종목별 일별 대차체결, 대차상환, 대차잔고 주식수 및 잔고 금액, 기관/외국인 비중.
- **활용 가치**:
  - 편출 유력 종목이나 CAP 축소(예: 25% → 1.4% 폭락) 대상 종목에 대해 **기관/외국인의 선행 대차잔고 급증(선제적 공매도 헷지)** 발생 여부 탐지.
  - 리밸런싱 당일 실제 시장충격이 발생하기 전 시장이 해당 이벤트를 얼마나 선반영(Priced-in)하고 있는지 수급 압력 지표로 활용.

### 4.4 주식분포현황(결산기준) 취급 주의사항
- **화면 ID**: `BIP_CNTS01047V` (주식분포현황 - 결산기준)
- **제공 데이터**: 최대주주 및 특수관계인, 정부/기관, 외국인, 소액주주(기타)의 지분율 및 주주수 원장.
- **⚠️ 사용 규율 (최후의 폴백으로만 사용)**:
  - 이 데이터는 **연 1회(또는 반기) 결산 시점 기준**이므로 심사 기준일과의 시점 불일치가 매우 큽니다.
  - 자사주, 보호예수, 기관 블록 등 유동/비유동 판정 산출식이 복잡하여 자의적 가정이 개입될 위험이 있습니다.
  - 따라서 **유동비율 산정의 1차 소스로 사용하는 것을 엄격히 금지**하며, 지수기관 공식 유동비율 및 WiseReport 등 외부 집계치가 전무하여 분석이 불가능할 때에 한해 **'최후의 폴백(Fallback)'**으로만 제한적으로 검토하고, 반드시 `추정 유동비율(SEIBRO 결산주식분포 역산)`임을 보고서에 명시해야 합니다.


