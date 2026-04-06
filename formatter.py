"""
formatter.py - 텔레그램 브리핑 메시지 포맷터

텔레그램 MarkdownV2 형식으로 보기 좋게 포맷팅합니다.
"""

import re
from datetime import datetime
from typing import List

from ai_filter import FilteredItem


class BriefingFormatter:
    """FilteredItem 목록 → 텔레그램 메시지 문자열 변환"""

    # 영향도별 이모지
    IMPACT_EMOJI = {"상": "🔴", "중": "🟡", "하": "🟢"}
    # 방향별 이모지
    DIRECTION_EMOJI = {"긍정": "📈", "부정": "📉", "중립": "➡️"}
    # 세션 제목
    SESSION_TITLE = {
        "morning": "📰 장전 브리핑 (08:30)",
        "afternoon": "📊 장후 브리핑 (16:00)",
    }

    def build_message(self, items: List[FilteredItem], session: str) -> str:
        """최종 텔레그램 메시지 생성"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        title = self.SESSION_TITLE.get(session, "📰 브리핑")

        lines = [
            f"*{title}*",
            f"_{now} 기준 · 노이즈 스캐너_",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        if not items:
            lines.append("\n⚪ 현재 시장에 영향을 줄 핵심 재료가 없습니다.")
        else:
            # 영향도 '상' 우선 정렬
            priority = {"상": 0, "중": 1, "하": 2}
            sorted_items = sorted(items, key=lambda x: priority.get(x.impact, 3))

            for i, item in enumerate(sorted_items, 1):
                impact_e = self.IMPACT_EMOJI.get(item.impact, "⚪")
                dir_e = self.DIRECTION_EMOJI.get(item.direction, "➡️")

                lines.append(
                    f"\n{impact_e} *{self._escape(item.theme)}*  {dir_e} {item.direction}"
                )
                lines.append(f"  {self._escape(item.summary)}")
                if item.url:
                    lines.append(f"  [원문]({item.url})")

        lines += [
            "\n━━━━━━━━━━━━━━━━━━━━",
            "🔍 영향도: 🔴상 · 🟡중 · 🟢하",
        ]
        return "\n".join(lines)

    @staticmethod
    def _escape(text: str) -> str:
        """텔레그램 MarkdownV2 특수문자 이스케이프"""
        # MarkdownV2에서 이스케이프 필요한 문자들
        special = r"\_*[]()~`>#+-=|{}.!"
        return re.sub(f"([{re.escape(special)}])", r"\\\1", text)


# ─────────────────────────────────────────────────────────────────────────────

"""
telegram_bot.py - 텔레그램 봇 전송 모듈
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
        텔레그램 메시지 최대 길이: 4096자
        """
        MAX_LEN = 4096
        chunks = [message[i : i + MAX_LEN] for i in range(0, len(message), MAX_LEN)]

        for chunk in chunks:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=True,  # 링크 미리보기 비활성화
                )
                logger.info(f"텔레그램 전송 성공 ({len(chunk)}자)")
            except Exception as e:
                # MarkdownV2 파싱 오류 발생 시 plain text로 재시도
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
