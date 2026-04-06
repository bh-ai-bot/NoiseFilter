import asyncio
import json
import logging
import re
import aiohttp
from dataclasses import dataclass
from typing import List

from collector import RawArticle
from config import Config

logger = logging.getLogger("AIFilter")

@dataclass
class FilteredItem:
    theme: str
    summary: str
    impact: str
    direction: str
    source: str
    url: str
    raw_title: str

class AINoiseFilter:
    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.gemini_api_key
        # 아까 성공했던 v1 주소와 2.0 모델 조합 유지
        self.api_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={self.api_key}"

    async def filter_and_summarize(self, articles: List[RawArticle], session: str) -> List[FilteredItem]:
        if not articles: return []
        
        batch_size = 15
        all_items = []
        
        async with aiohttp.ClientSession() as http_session:
            for i in range(0, len(articles), batch_size):
                batch = articles[i : i + batch_size]
                items = await self._process_batch_direct(http_session, batch)
                all_items.extend(items)
                await asyncio.sleep(10)
        return all_items

    async def _process_batch_direct(self, http_session, articles):
        articles_text = "\n".join([f"제목: {a.title}\n내용: {a.summary[:150]}" for a in articles])
        
        # [수정] 에러를 일으키는 responseMimeType 옵션을 완전히 제거
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"너는 금융 전문가야. 다음 뉴스 중 주가 영향이 큰 것만 골라 JSON 리스트로만 답해. 설명은 절대 하지마.\n포맷: [{{ \"theme\": \"종목\", \"summary\": \"내용\", \"impact\": \"상/중/하\", \"direction\": \"긍정/부정/중립\", \"source\": \"출처\", \"url\": \"링크\", \"raw_title\": \"제목\" }}]\n\n뉴스 목록:\n{articles_text}"
                }]
            }]
        }

        try:
            async with http_session.post(self.api_url, json=payload) as resp:
                if resp.status != 200:
                    err_msg = await resp.text()
                    logger.error(f"API 호출 실패 ({resp.status}): {err_msg}")
                    return []

                result = await resp.json()
                
                if "candidates" not in result or not result['candidates']:
                    return []

                raw_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # [강력한 보호] AI가 텍스트를 섞어도 [ ] 구간만 찾아서 파싱
                json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                if not json_match:
                    logger.warning(f"JSON 패턴 미발견: {raw_text[:100]}")
                    return []
                
                data = json.loads(json_match.group())
                
                return [FilteredItem(
                    theme=d.get("theme", "기타"),
                    summary=d.get("summary", ""),
                    impact=d.get("impact", "하"),
                    direction=d.get("direction", "중립"),
                    source=d.get("source", "정보"),
                    url=d.get("url", ""),
                    raw_title=d.get("raw_title", "")
                ) for d in data]
        except Exception as e:
            logger.error(f"처리 중 오류: {e}")
            return []