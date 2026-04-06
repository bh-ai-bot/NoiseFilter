# 🔍 노이즈 스캐너 (Noise Scanner)

> 매일 주식 시장의 노이즈를 제거하고 핵심만 전달하는 텔레그램 금융 AI 에이전트

---

## 📐 아키텍처

```
[데이터 소스]          [수집]          [AI 필터]       [전송]
 DART 공시      ──┐
 네이버 금융    ──┤  Collector  →  Claude API  →  Telegram Bot
 Yahoo Finance ──┤  (병렬 수집)    (노이즈 제거     (08:30 / 16:00)
 연합인포맥스   ──┘               + 3줄 요약)
```

## ⚡ 빠른 시작

### 1. 설치

```bash
git clone https://github.com/your-repo/noise-scanner.git
cd noise-scanner
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열고 API 키 3개 입력
```

**필요한 키 3개:**

| 변수 | 발급처 | 비고 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Claude API |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 @BotFather | `/newbot` 명령어 |
| `TELEGRAM_CHAT_ID` | getUpdates API | 채널/DM ID |

### 3. 관심 키워드 설정

`config.py`의 `keywords` 리스트를 본인 투자 섹터에 맞게 수정:

```python
keywords: List[str] = [
    "반도체", "HBM", "SK하이닉스",   # 반도체 섹터
    "이차전지", "배터리", "에코프로",  # 배터리 섹터
    "테슬라", "엔비디아", "AI",       # 미국 빅테크
    # 본인 관심 종목 추가...
]
```

### 4. 실행

```bash
# 테스트 (텔레그램 미전송, 콘솔 출력만)
python main.py --test

# 장전 브리핑
python main.py --session morning

# 장후 브리핑
python main.py --session afternoon
```

---

## ☁️ 배포 가이드

### 방법 A: GitHub Actions (무료, 권장)

1. 이 레포를 GitHub에 Push
2. **Settings → Secrets and variables → Actions** 에서 환경 변수 3개 추가
3. `.github/workflows/noise_scanner.yml` 이 자동으로 스케줄 실행

```
장전: 매일 KST 08:30 (UTC 23:30)
장후: 매일 KST 16:00 (UTC 07:00)
```

> ⚠️ GitHub Actions 무료 플랜: 월 2,000분 제공. 하루 2회 실행 시 월 ~60분 사용 (여유 충분)

### 방법 B: Google Cloud Run Jobs

```bash
# 1. 도커 이미지 빌드
docker build -t noise-scanner .

# 2. GCR에 푸시
docker tag noise-scanner gcr.io/YOUR_PROJECT/noise-scanner
docker push gcr.io/YOUR_PROJECT/noise-scanner

# 3. Cloud Run Job 생성
gcloud run jobs create noise-scanner-morning \
  --image gcr.io/YOUR_PROJECT/noise-scanner \
  --command "python,main.py,--session,morning" \
  --set-env-vars ANTHROPIC_API_KEY=...,TELEGRAM_BOT_TOKEN=...,TELEGRAM_CHAT_ID=...

# 4. Cloud Scheduler로 트리거
gcloud scheduler jobs create http noise-scanner-morning-trigger \
  --schedule "30 23 * * 0-4" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT/jobs/noise-scanner-morning:run" \
  --time-zone "Asia/Seoul"
```

---

## 📱 텔레그램 출력 예시

```
📰 장전 브리핑 (08:30)
_2025-01-15 08:30 기준 · 노이즈 스캐너_
━━━━━━━━━━━━━━━━━━━━

🔴 SK하이닉스  📈 긍정
  HBM3E 엔비디아 공급 단가 20% 인상 확정, 2Q 영업이익 상향 요인
  [원문](https://...)

🔴 이차전지  📉 부정
  미국 IRA 전기차 세액공제 요건 강화 법안 상원 통과
  [원문](https://...)

🟡 금리  ➡️ 중립
  연준 의사록, 인플레 우려 지속 · 3월 인하 기대 후퇴
  [원문](https://...)
━━━━━━━━━━━━━━━━━━━━
🔍 영향도: 🔴상 · 🟡중 · 🟢하
```

---

## 💰 예상 비용

| 항목 | 단가 | 월간 예상 |
|------|------|----------|
| Claude API (Sonnet) | $3 / 1M input tokens | ~$2~5 |
| GitHub Actions | 무료 | $0 |
| **합계** | | **~$2~5/월** |

> 기사 수집량과 배치 크기에 따라 달라집니다.
> `config.py`의 `max_articles_per_source`, `ai_batch_size` 조절로 비용 관리 가능.

---

## 🛠 파일 구조

```
noise_scanner/
├── main.py          # 메인 실행 파일 (진입점)
├── config.py        # 환경 변수 & 설정
├── collector.py     # 멀티소스 데이터 수집기
├── ai_filter.py     # Claude API 노이즈 필터 & 요약
├── formatter.py     # 텔레그램 메시지 포맷터
├── telegram_bot.py  # 텔레그램 봇 전송
├── requirements.txt
├── .env.example     # 환경 변수 템플릿
└── .github/
    └── workflows/
        └── noise_scanner.yml  # GitHub Actions 스케줄러
```
