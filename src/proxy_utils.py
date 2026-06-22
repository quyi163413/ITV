# src/proxy_utils.py
import asyncio
import aiohttp
from urllib.parse import urlparse
from src.config import ENABLE_GITHUB_PROXY, HEADERS, TIMEOUT
from src.logger import logger

GITHUB_RAW_PROXIES = [
    "https://ghproxy.net/",
    "https://gh-proxy.19860519.xyz/",
    "https://raw.kkgithub.com/",
]
GITHUB_PROXY_TIMEOUT = 15

def should_proxy(url: str) -> bool:
    if not ENABLE_GITHUB_PROXY:
        return False
    return "raw.githubusercontent.com" in url

def build_proxy_url(original_url: str, proxy_prefix: str) -> str:
    if proxy_prefix.startswith(("https://ghproxy.net/", "https://gh.api.99988866.xyz/")):
        return f"{proxy_prefix}{original_url}"
    elif "raw.staticdn.net" in proxy_prefix or "raw.githubusercontents.com" in proxy_prefix:
        parsed = urlparse(original_url)
        return f"{proxy_prefix}{parsed.path}"
    else:
        return f"{proxy_prefix}{original_url}"

async def fetch_with_proxy_fallback(session: aiohttp.ClientSession, url: str):
    if not should_proxy(url):
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as resp:
                if resp.status == 200:
                    return await resp.text(), None
                return None, None
        except Exception as e:
            logger.debug(f"直连 {url} 失败: {e}")
            return None, None

    for proxy_prefix in GITHUB_RAW_PROXIES:
        proxy_url = build_proxy_url(url, proxy_prefix)
        try:
            async with session.get(proxy_url, timeout=GITHUB_PROXY_TIMEOUT, headers=HEADERS) as resp:
                if resp.status == 200:
                    logger.info(f"✅ 代理拉取成功: {proxy_prefix[:40]}...")
                    return await resp.text(), proxy_prefix
                else:
                    logger.debug(f"代理 {proxy_prefix} 返回 {resp.status}")
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ 代理 {proxy_prefix} 超时")
        except Exception as e:
            logger.debug(f"代理 {proxy_prefix} 失败: {e}")
        await asyncio.sleep(0.2)
    return None, None
