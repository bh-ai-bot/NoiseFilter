"""
telegram_bot.py - 텔레그램 봇 전송 모듈

python-telegram-bot v20+ (async 방식) 사용.
봇 설정 방법:
    1. 텔레그램에서 @BotFather 에게 /newbot 명령어 전송
    2. 봇 토큰 발급 → TELEGRAM_BOT_TOKEN 환경 변수에 저장
    3. 채널/그룹에 봇을 추가하고 채팅 ID를 TELEGRAM_CHAT_ID에 저장
       (채팅 ID 확인: https://api.telegram.org/bot<TOKEN>/getUpdates)
"""

import logging
from telegram import Bot
from telegram.constants import ParseMode

from config import Config

logger = logging.getLogger("TelegramSender")


class TelegramSender:
    """텔레그램 봇으로 메시지를 전송하는 클래스"""

    def __init__(self, config: Config):
        self.bot = Bot(token=config.telegram_bot_token)
        self.chat_id = config.telegram_chat_id

    async def send(self, message: str) -> None:
        """
        메시지를 텔레그램으로 전송.

        메시지가 4096자 초과 시 자동으로 분할 전송합니다.
        """
        MAX_LEN = 4096
        chunks = [message[i : i + MAX_LEN] for i in range(0, len(message), MAX_LEN)]

        for chunk in chunks:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=True,
                )
                logger.info(f"텔레그램 전송 성공 ({len(chunk)}자)")
            except Exception as e:
                # MarkdownV2 파싱 오류 시 plain text로 재시도
                logger.warning(f"MarkdownV2 전송 실패, plain text로 재시도: {e}")
                try:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=chunk,
                        disable_web_page_preview=True,
                    )
                except Exception as e2:
                    logger.error(f"텔레그램 전송 최종 실패: {e2}")
                    raise
