"""
collector.py - 멀티소스 데이터 수집기

수집 대상:
    1. 네이버 금융 뉴스 (RSS)
    2. DART 공시 (RSS)
    3. Yahoo Finance (yfinance + RSS)
    4. 연합인포맥스 (RSS)

각 소스는 독립적인 async 함수로 구현되어 병렬 수집됩니다.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

import aiohttp
import feedparser
import yfinance as yf
from bs4 import BeautifulSoup

from config import Config

logger = logging.getLogger("Collector")


@dataclass
class RawArticle:
    """수집된 원시 기사 데이터"""
    source: str           # 출처 (naver, dart, yahoo, yonhap 등)
    title: str            # 제목
    summary: str          # 요약/본문 앞부분
    url: str              # 원문 링크
    published: str        # 발행 시각 (문자열)
    article_id: str       # 중복 제거용 해시 ID

    @classmethod
    def from_feed_entry(cls, source: str, entry) -> "RawArticle":
        """feedparser entry → RawArticle 변환"""
        title = entry.get("title", "").strip()
        summary = BeautifulSoup(
            entry.get("summary", entry.get("description", "")), "html.parser"
        ).get_text(separator=" ", strip=True)[:500]
        url = entry.get("link", "")
        published = entry.get("published", entry.get("updated", str(datetime.now())))
        # 제목 + URL 해시로 중복 방지
        article_id = hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]
        return cls(source, title, summary, url, published, article_id)


class DataCollector:
    """모든 소스에서 비동기로 기사를 수집하는 통합 수집기"""

    def __init__(self, config: Config):
        self.config = config
        self._seen_ids: set = set()  # 중복 제거용 집합

    async def collect_all(self) -> List[RawArticle]:
        """모든 소스 병렬 수집 후 합쳐서 반환"""
        tasks = [
            self._collect_naver_finance(),
            self._collect_dart_disclosures(),
            self._collect_yahoo_finance(),
            self._collect_yonhap_economy(),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        articles: List[RawArticle] = []
        source_names = ["Naver", "DART", "Yahoo", "Yonhap"]
        for name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.warning(f"{name} 수집 실패: {result}")
            else:
                articles.extend(result)
                logger.info(f"{name}: {len(result)}건 수집")

        # 키워드 필터링 (관심 섹터 우선)
        filtered = self._keyword_filter(articles)
        logger.info(f"키워드 필터 후: {len(filtered)}건")
        return filtered

    # ─── 1. 네이버 금융 뉴스 ────────────────────────────────────
    async def _collect_naver_finance(self) -> List[RawArticle]:
        """
        네이버 금융 뉴스 RSS 피드 수집
        URL: https://finance.naver.com/news/news_list.nhn
        RSS: https://stock.pstatic.net/stock/research/debenture/...
        """
        rss_urls = [
            # 네이버 경제 뉴스 RSS
            "https://www.fnnews.com/rss/fn_realnews_stock.xml",
            # 매일경제 증권 뉴스
            "https://www.mk.co.kr/rss/40300001/",
            # 한국경제 증권
            "https://www.hankyung.com/feed/securities",
        ]
        return await self._parse_rss_feeds("naver", rss_urls)

    # ─── 2. DART 공시 (전자공시시스템) ─────────────────────────
    async def _collect_dart_disclosures(self) -> List[RawArticle]:
        """
        DART 최신 공시 RSS 수집
        공식 RSS: https://dart.fss.or.kr/api/shareholder.rss
        
        참고: DART Open API 키가 있으면 더 정확한 데이터 수집 가능
              https://opendart.fss.or.kr 에서 무료 발급
        """
        rss_urls = [
            # DART 주요 공시 RSS (유상증자, 주요사항보고 등)
            "https://dart.fss.or.kr/rss/shareholder.rss",
            "https://dart.fss.or.kr/rss/major.rss",
        ]
        return await self._parse_rss_feeds("dart", rss_urls)

    # ─── 3. Yahoo Finance (미국 시장) ───────────────────────────
    async def _collect_yahoo_finance(self) -> List[RawArticle]:
        """
        Yahoo Finance RSS + yfinance 라이브러리로 미국 시장 뉴스 수집
        
        yfinance는 동기 라이브러리이므로 executor에서 실행합니다.
        """
        articles = []

        # RSS 피드 방식
        rss_urls = [
            "https://finance.yahoo.com/rss/topstories",
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA,TSLA,AAPL&region=US&lang=en-US",
        ]
        articles += await self._parse_rss_feeds("yahoo", rss_urls)

        # yfinance 방식 (관심 종목 뉴스)
        loop = asyncio.get_event_loop()
        yf_articles = await loop.run_in_executor(None, self._fetch_yfinance_news)
        articles += yf_articles

        return articles

    def _fetch_yfinance_news(self) -> List[RawArticle]:
        """yfinance로 티커별 최신 뉴스 수집 (동기 함수, executor 실행)"""
        tickers = ["NVDA", "TSLA", "AAPL", "MSFT", "005930.KS", "000660.KS"]
        articles = []
        for ticker_symbol in tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                news = ticker.news or []
                for item in news[:5]:  # 티커당 최대 5건
                    title = item.get("title", "").strip()
                    if not title:
                        continue
                    url = item.get("link", "")
                    summary = item.get("summary", "")[:500]
                    published = str(
                        datetime.fromtimestamp(item.get("providerPublishTime", 0))
                    )
                    article_id = hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]
                    articles.append(
                        RawArticle("yfinance", title, summary, url, published, article_id)
                    )
            except Exception as e:
                logger.debug(f"yfinance {ticker_symbol} 실패: {e}")
        return articles

    # ─── 4. 연합인포맥스 ────────────────────────────────────────
    async def _collect_yonhap_economy(self) -> List[RawArticle]:
        """연합뉴스 경제 섹션 RSS 수집"""
        rss_urls = [
            "https://www.yonhapnewstv.co.kr/category/news/economy/feed/",
            "https://www.yna.co.kr/rss/economy.xml",
        ]
        return await self._parse_rss_feeds("yonhap", rss_urls)

    # ─── 공통 RSS 파서 ──────────────────────────────────────────
    async def _parse_rss_feeds(
        self, source: str, urls: List[str]
    ) -> List[RawArticle]:
        """RSS URL 목록을 병렬로 파싱하여 RawArticle 리스트 반환"""
        articles = []
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; NoiseScanner/1.0; "
                "+https://github.com/your-repo/noise-scanner)"
            )
        }

        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            for url in urls:
                try:
                    async with session.get(url) as resp:
                        text = await resp.text(errors="replace")
                    feed = feedparser.parse(text)
                    for entry in feed.entries[: self.config.max_articles_per_source]:
                        article = RawArticle.from_feed_entry(source, entry)
                        # 중복 제거
                        if article.article_id not in self._seen_ids:
                            if len(article.title) >= self.config.min_article_length // 2:
                                self._seen_ids.add(article.article_id)
                                articles.append(article)
                except Exception as e:
                    logger.debug(f"RSS 파싱 실패 ({url}): {e}")

        return articles

    # ─── 키워드 1차 필터 ────────────────────────────────────────
    def _keyword_filter(self, articles: List[RawArticle]) -> List[RawArticle]:
        """
        관심 키워드가 포함된 기사는 앞으로, 나머지는 뒤로 정렬.
        완전히 제거하지 않고 순서로만 우선순위를 부여합니다
        (AI가 2차로 더 정밀하게 필터링하기 때문).
        """
        keywords = [k.lower() for k in self.config.keywords]

        def priority(article: RawArticle) -> int:
            text = (article.title + " " + article.summary).lower()
            return sum(1 for kw in keywords if kw in text)

        return sorted(articles, key=priority, reverse=True)
