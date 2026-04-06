import asyncio
import aiohttp
from config import Config

async def check_gemini_models():
    config = Config()
    api_key = config.gemini_api_key
    
    # v1과 v1beta 두 군데 다 찔러보자
    versions = ['v1', 'v1beta']
    
    async with aiohttp.ClientSession() as session:
        for ver in versions:
            url = f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}"
            print(f"\n🔍 [{ver}] 버전 확인 중: {url[:60]}...")
            
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ [{ver}] 연결 성공! 지원 모델 목록:")
                        for model in data.get('models', []):
                            # 우리가 쓰려는 모델이 있는지 강조해서 출력
                            m_name = model['name']
                            if 'gemini' in m_name.lower():
                                print(f"  ⭐ {m_name}")
                            else:
                                print(f"  - {m_name}")
                    else:
                        err_text = await resp.text()
                        print(f"❌ [{ver}] 연결 실패 (코드: {resp.status})")
                        print(f"   메시지: {err_text}")
            except Exception as e:
                print(f"⚠️ 에러 발생: {e}")

if __name__ == "__main__":
    print("🚀 Gemini API 모델 지원 여부 체크 시작...")
    asyncio.run(check_gemini_models())