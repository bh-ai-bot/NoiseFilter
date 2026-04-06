"""
config.py - 환경 변수 및 설정 관리

.env 파일 또는 환경 변수에서 설정을 로드합니다.
민감한 키는 절대 코드에 하드코딩하지 마세요!

필수 환경 변수:
    ANTHROPIC_API_KEY   - Claude API 키
    TELEGRAM_BOT_TOKEN  - 텔레그램 봇 토큰
    TELEGRAM_CHAT_ID    - 텔레그램 채널/채팅 ID
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# .env 파일 자동 로드 (로컬 개발용)
load_dotenv()


@dataclass
class Config:
    # 앤트로픽 대신 제미나이로 변경
    gemini_api_key: str = field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY", "")
    )
    telegram_bot_token: str = field(
        default_factory=lambda: os.environ["TELEGRAM_BOT_TOKEN"]
    )
    telegram_chat_id: str = field(
        default_factory=lambda: os.environ["TELEGRAM_CHAT_ID"]
    )

    # ─── 관심 키워드 (본인 투자 섹터에 맞게 수정) ─────────────
    # 이 키워드가 포함된 뉴스를 우선 수집하고 AI 분석에 반영합니다.
    keywords: List[str] = field(
        default_factory=lambda: [
            "반도체", "HBM", "SK하이닉스", "삼성전자",
            "이차전지", "배터리", "에코프로", "LG에너지솔루션",
            "AI", "인공지능", "엔비디아", "테슬라",
            "바이오", "제약", "금리", "환율", "코스피", "나스닥",
        ]
    )

    # ─── 수집 설정 ─────────────────────────────────────────────
    # 최대 수집 기사 수 (많을수록 API 비용 증가, 100~200 권장)
    max_articles_per_source: int = 30

    # 최소 기사 길이 (너무 짧은 기사 제외)
    min_article_length: int = 50

    # HTTP 요청 타임아웃 (초)
    request_timeout: int = 10

    # ─── AI 필터 설정 ──────────────────────────────────────────
    # Claude 모델 (claude-sonnet-4-20250514 권장)
    claude_model: str = "claude-sonnet-4-20250514"

    # 한 번에 AI에 넘길 최대 기사 수 (토큰 비용 관리)
    ai_batch_size: int = 20

    # AI가 선별해서 돌려주는 최종 핵심 기사 수
    max_output_items: int = 10
