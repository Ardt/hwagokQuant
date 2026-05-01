# 프로젝트 플로우

## 개요

```
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│      train.py          │  │    portfolio.py        │  │      trade.py          │
│  (백그라운드, 자동)      │  │  (대화형, 수동)         │  │  (대화형, 시그널)       │
├────────────────────────┤  ├────────────────────────┤  ├────────────────────────┤
│ 1. 마켓별 유니버스 조회  │  │ 1. 포트폴리오 생성      │  │ 1. 포트폴리오 선택      │
│ 2. + 포트폴리오 추가종목 │  │ 2. 종목 추가/제거       │  │ 2. 마켓 감지           │
│ 3. OHLCV + 매크로 수집  │  │ 3. 수동 매수/매도       │  │ 3. 저장된 모델 로드     │
│ 4. 피처 생성            │  │ 4. 목표 배분 설정       │  │ 4. 시그널 생성         │
│ 5. LSTM 학습/종목별     │  │ 5. 리포트 조회          │  │ 5. 앙상블 조정         │
│ 6. 모델 저장            │  │ 6. 가격 갱신           │  │ 6. 모의 매매           │
│ 7. 백테스트 + 기록      │  │ 7. 포트폴리오 삭제      │  │ 7. DB 기록            │
│                        │  │                        │  │                        │
│ 읽기: DB + config      │  │ 읽기/쓰기: DB          │  │ 읽기: DB + 모델        │
│ 쓰기: models/*.pt      │  │                        │  │ 쓰기: DB (거래)        │
└───────────┬────────────┘  └───────────┬────────────┘  └───────────┬────────────┘
            │                           │                           │
            └───── data/models/*.pt ────┘───── data/portfolio.db ───┘
```

---

## 마켓 감지

```
ticker.isdigit() → KRX (예: "005930", "000660")
그 외             → US  (예: "AAPL", "MSFT")

train.py:  각 마켓별 유니버스 + 포트폴리오 추가 종목 학습
trade.py:  포트폴리오 선택 → 종목에서 마켓 감지 → 해당 파이프라인 사용
빈 포트폴리오: 건너뜀 (학습/매매 없음)
```

---

## 마켓 설정 (config.py → MARKETS dict)

| 설정 | US | KRX |
|------|-----|-----|
| 통화 | USD | KRW |
| 자본금 | $100,000 | ₩100,000,000 |
| OHLCV 소스 | yfinance | pykrx |
| 종목 소스 | Wikipedia (S&P500 + NASDAQ100) | pykrx (KOSPI + KOSDAQ) |
| 매크로 소스 | FRED (VIX, 기준금리, 국채스프레드, CPI, 실업률, HY스프레드) | FRED VIX + 한국 기준금리, CPI, 실업률 |
| 감성분석 | FinBERT (영문 뉴스) | 비활성 |
| 종목코드 형식 | 알파벳 (AAPL) | 6자리 숫자 (005930) |

---

## train.py — 모델 학습 파이프라인

### 1단계. 유니버스 + 포트폴리오 추가 종목
```
각 마켓 (US, KRX)에 대해:
  get_universe() → 시가총액 상위 100개 종목
  + 포트폴리오 종목 (보유 + 관심) 중 유니버스에 없는 것
  = 통합 학습 리스트
```

### 2단계. 데이터 수집
```
US:  Wikipedia → 종목 → yfinance → OHLCV (증분)
KRX: pykrx → KOSPI/KOSDAQ 시가총액순 → OHLCV (증분)
     캐시: data/tickers.csv (US), data/krx_tickers.csv (KRX)
     캐시: data/ohlcv.csv (US), data/krx_ohlcv.csv (KRX)
```

### 3단계. 피처 엔지니어링 (`src/data/features.py`)
```
원시 OHLCV → 17개 기술적 지표 (양 마켓 동일):
            추세: SMA(20), SMA(50), EMA(12), MACD, MACD Signal, MACD Hist
            모멘텀: RSI, Stochastic RSI
            변동성: Bollinger Bands (High/Low/Width), ATR
            거래량: OBV
            수익률: 1일, 5일, 20일 변동성
         → MinMaxScaler (0-1 정규화)
         → 슬라이딩 윈도우 → 60일 시퀀스
```

### 4단계. 감성분석 (`src/data/sentiment.py`)
```
US:  yfinance 뉴스 → FinBERT → 점수 (-1 ~ +1)
KRX: 비활성 (0.0 고정) — 한국어 FinBERT 미구현
```

### 5단계. 매크로 데이터
```
US:  FRED → VIX, 기준금리, 국채스프레드, CPI, 실업률, HY스프레드
KRX: FRED VIX (글로벌 공포 프록시) + 한국 기준금리, CPI, 실업률
     캐시: data/fred.csv (US), data/krx_macro.csv (KRX)
```

### 6단계. LSTM 학습 (`src/model/lstm.py`)
```
결합된 피처를 60일 시퀀스로
         → 학습/검증 분할 (80/20, walk-forward)
         → PyTorch LSTM (2층, 64 hidden, dropout 0.2)
         → 이진 분류: 내일 상승(1) 또는 하락(0)?
         → 조기 종료 (patience=10)
         → 저장 → data/models/{ticker}_lstm.pt
```

### 7단계. 백테스트 (`src/backtest/engine.py`)
```
모델 예측 → 시그널 (>0.5=매수, <0.5=매도)
         → Walk-forward 백테스트 (손절 -5%, 익절 +10%)
         → 지표: 수익률, 샤프비율, 승률, 최대낙폭
         → 출력: data/training_results.csv (US), data/training_results_krx.csv (KRX)
```

---

## trade.py — 시그널 생성 + 모의 매매

### 1단계. 포트폴리오 선택
```
DB → 포트폴리오 목록 (마켓 + 통화 표시) → 하나 선택
  → 종목에서 마켓 감지
```

### 2단계. 시그널 생성
```
포트폴리오 종목 → OHLCV + 매크로 수집 (마켓별)
         → 피처 생성 (동일 파이프라인)
         → 저장된 모델 로드 (data/models/{ticker}_lstm.pt)
         → 예측 → 종목별 원시 시그널
```

### 3단계. 앙상블 조정 (`src/model/ensemble.py`)
```
원시 시그널 + 매크로 상태 + 포트폴리오 상태
         → 리스크 승수 (VIX > 30 → 매수 축소)
         → 집중도 체크 (한 종목 >25% → 축소)
         → 현금 체크 (현금 <10% → 매수 축소)
         → 출력: 조정된 시그널 (매수 → 관망 가능)
```

### 4단계. 모의 매매 실행
```
조정된 시그널 → 매매 계획:
  매수: 현금을 매수 시그널 종목에 균등 분배
  매도: sell_ratio = 1 - probability
  관망: 기록만
         → 제안된 매매 표시 → 확인
         → 모의 매매 실행 (시뮬레이션 체결)
         → 포트폴리오 DB에 거래 기록
         → 스냅샷 저장
```

---

## portfolio.py — 포트폴리오 관리

```
대화형 메뉴:
  1. 포트폴리오 목록
  2. 포트폴리오 생성 (이름, 자본금, 종목)
  3. 리포트 조회 (손익, 보유, 집중도)
  4. 종목 추가/제거 (관심목록)
  5. 수동 매수/매도 (거래 기록)
  6. 목표 배분 설정
  7. 가격 갱신 (yfinance)
  8. 포트폴리오 삭제

마켓은 종목에서 자동 감지 — 별도 플래그 불필요.
KRX 종목: 005930, 000660, 035420, ...
US 종목: AAPL, MSFT, GOOGL, ...
```

---

## 공유 인프라

| 컴포넌트 | 용도 |
|----------|------|
| `config.py` | 공유 파라미터 + MARKETS dict (마켓별 설정) |
| `src/market.py` | `detect_market()`, `detect_portfolio_market()`, `get_config()` |
| `src/logger.py` | 콘솔 (INFO) + 파일 (DEBUG) 로깅 → `data/pipeline.log` |
| `src/notify.py` | 알림: Slack, Discord, Telegram, Email |
| `src/data/cache.py` | TTL 관리: `python -m src.data.cache list|clear` |
| `src/data/features.py` | 기술적 지표 + 동적 피처 준비 |
| `src/data/collector.py` | US: yfinance + Wikipedia |
| `src/data/krx_collector.py` | KRX: pykrx (KOSPI + KOSDAQ) |
| `src/data/fred.py` | US 매크로 (FRED) |
| `src/data/krx_macro.py` | 한국 매크로 (FRED) |
| `src/data/sentiment.py` | FinBERT 감성분석 (US만) |
| `src/portfolio/db.py` | SQLAlchemy ORM (SQLite/PostgreSQL) |
| `src/portfolio/manager.py` | 24개 포트폴리오 함수 (손익, 리스크, 배분, 리포팅) |

## 알림

발송 시점:
- **강한 성과 종목 관심목록 추가** — 마켓별
- **약한 성과 종목 제거** — 마켓별
- **매매 실행** — 매수 금액, 매도 손익

## 캐시 파일
| 파일 | 소스 | 마켓 | 만료 |
|------|------|------|------|
| `data/tickers.csv` | Wikipedia | US | 10일 |
| `data/ohlcv.csv` | yfinance | US | 만료 없음 (증분) |
| `data/fred.csv` | FRED | US | 만료 없음 (증분) |
| `data/krx_tickers.csv` | pykrx | KRX | 10일 |
| `data/krx_ohlcv.csv` | pykrx | KRX | 만료 없음 (증분) |
| `data/krx_macro.csv` | FRED | KRX | 만료 없음 (증분) |
| `data/portfolio.db` | 로컬 | 공유 | 만료 없음 |
| `data/models/*.pt` | train.py | 양쪽 | 만료 없음 (수동 재학습) |
