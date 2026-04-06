"""
노이즈 스캐너 (Noise Scanner) - 메인 실행 파일
매일 주식 시장의 핵심 재료만 선별해서 텔레그램으로 브리핑하는 금융 AI 에이전트.

실행 방법:
    python main.py --session morning    # 장전 브리핑 (08:30)
    python main.py --session afternoon  # 장후 브리핑 (16:00)
    python main.py --test               # 테스트 전송
"""

import argparse
import asyncio
import logging
from datetime import datetime

from collector import DataCollector
from ai_filter import AINoiseFilter
from formatter import BriefingFormatter
from telegram_bot import TelegramSender
from config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("NoiseScanner")


async def run_briefing(session: str, test_mode: bool = False):
    """
    전체 파이프라인 실행:
    1. 데이터 수집 → 2. AI 필터링 → 3. 포맷팅 → 4. 텔레그램 전송
    """
    config = Config()
    logger.info(f"===== 노이즈 스캐너 시작 | 세션: {session} =====")

    # 1. 데이터 수집
    logger.info("데이터 수집 시작...")
    collector = DataCollector(config)
    raw_articles = await collector.collect_all()
    logger.info(f"수집 완료: 총 {len(raw_articles)}건")

    if not raw_articles:
        logger.warning("수집된 기사가 없습니다. 종료합니다.")
        return

    # 2. AI 노이즈 필터링 (Claude API)
    logger.info("AI 노이즈 필터링 시작...")
    ai_filter = AINoiseFilter(config)
    filtered_items = await ai_filter.filter_and_summarize(raw_articles, session)
    logger.info(f"필터링 완료: {len(raw_articles)}건 → {len(filtered_items)}건 핵심 선별")

    # 3. 텔레그램 메시지 포맷팅
    logger.info("브리핑 포맷팅...")
    formatter = BriefingFormatter()
    message = formatter.build_message(filtered_items, session)

    # 4. 텔레그램 전송
    if test_mode:
        logger.info("[테스트 모드] 텔레그램 미전송. 메시지 미리보기:")
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60 + "\n")
    else:
        logger.info("텔레그램 전송 중...")
        sender = TelegramSender(config)
        await sender.send(message)
        logger.info("전송 완료!")

    logger.info("===== 노이즈 스캐너 완료 =====")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="노이즈 스캐너 - 주식 시장 핵심 브리핑")
    parser.add_argument(
        "--session",
        choices=["morning", "afternoon"],
        default="morning",
        help="브리핑 세션 (morning=장전 / afternoon=장후)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드 (텔레그램 미전송, 콘솔 출력만)",
    )
    args = parser.parse_args()

    asyncio.run(run_briefing(session=args.session, test_mode=args.test))
