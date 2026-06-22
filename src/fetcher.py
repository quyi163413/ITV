# src/fetcher.py
# 拉取模块：支持缓存、重试、代理轮换

import asyncio
import aiohttp
from src.config import HEADERS, TIMEOUT, RETRY_MAX_ATTEMPTS, ENABLE_RETRY, get_proxy_list
from src.logger import logger


class FetchError(Exception):
    pass


async def fetch_url_with_metadata(url: str, db, proxies=None):
    """
    拉取单个 URL 的内容，支持缓存和代理轮换重试
    
    Args:
        url: 要拉取的 URL
        db: 数据库连接（为 None 时禁用缓存）
        proxies: 代理列表，若为 None 则自动获取
    """
    if db:
        cached_content = await db.get_raw_source(url)
        if cached_content:
            logger.debug(f"✅ 使用缓存: {url}")
            return cached_content

    # 获取代理列表
    if proxies is None:
        proxies = get_proxy_list()
    
    # 判断是否为 GitHub raw 源
    is_github = "raw.githubusercontent.com" in url
    
    # 构造尝试顺序：先尝试直接（如果非GitHub），再尝试代理
    attempts = []
    if not is_github:
        attempts.append(("direct", url))
    # 代理尝试
    for proxy in proxies:
        # 避免重复添加代理前缀
        if url.startswith(proxy):
            proxy_url = url
        else:
            proxy_url = proxy + url if not url.startswith(proxy) else url
        attempts.append((proxy, proxy_url))
    
    # 去重：避免重复尝试相同URL
    seen = set()
    unique_attempts = []
    for label, attempt_url in attempts:
        if attempt_url not in seen:
            seen.add(attempt_url)
            unique_attempts.append((label, attempt_url))
    
    last_exception = None
    for label, attempt_url in unique_attempts:
        try:
            logger.info(f"🔄 拉取{' (代理: ' + label + ')' if label != 'direct' else ''}: {attempt_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(attempt_url, timeout=TIMEOUT, headers=HEADERS) as resp:
                    if resp.status != 200:
                        raise FetchError(f"HTTP {resp.status}")
                    content = await resp.text()
                    if db:
                        await db.set_raw_source(url, content)  # 用原始URL存缓存
                    return content
        except Exception as e:
            last_exception = e
            logger.warning(f"  尝试失败 ({label}): {e}")
            await asyncio.sleep(1)  # 短暂等待后重试下一个代理
    
    # 所有尝试都失败，抛出最后一个异常
    raise FetchError(str(last_exception) if last_exception else "所有代理尝试失败")


async def fetch_all_sources_incremental(sources: list, db, force_refresh: bool = False) -> dict:
    """
    并发拉取所有源，支持强制刷新
    
    Args:
        sources: 源 URL 列表
        db: 数据库连接
        force_refresh: 是否强制重新拉取（忽略缓存）
    
    Returns:
        {url: content} 字典
    """
    # 每个 fetch_url_with_metadata 内部自己创建会话，无需共享
    tasks = []
    for url in sources:
        if force_refresh:
            tasks.append(fetch_url_with_metadata(url, None))
        else:
            tasks.append(fetch_url_with_metadata(url, db))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    output = {}
    for url, res in zip(sources, results):
        if isinstance(res, Exception):
            logger.warning(f"⚠️ 拉取失败 {url}: {res}")
            # 如果不是强制刷新，尝试从缓存读取旧内容
            if not force_refresh and db:
                cached = await db.get_raw_source(url)
                if cached:
                    output[url] = cached
                    logger.info(f"📦 使用旧缓存: {url}")
                else:
                    output[url] = None
            else:
                output[url] = None
        else:
            output[url] = res
    return output
