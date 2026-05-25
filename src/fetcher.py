# src/fetcher.py
# 支持 HEAD 请求检测更新，无变化则跳过拉取，直接使用数据库缓存

import asyncio
import aiohttp
from src.config import HEADERS, TIMEOUT, RETRY_MAX_ATTEMPTS, RETRY_BACKOFF_FACTOR, RETRY_MAX_WAIT, ENABLE_RETRY
from src.database import get_db_cache

class FetchError(Exception):
    pass

async def check_source_modified(session: aiohttp.ClientSession, url: str, db) -> tuple:
    """
    通过 HEAD 请求检查源是否有更新。
    返回 (is_modified, cached_content, new_etag, new_last_modified)
    is_modified: True 表示有更新，需要拉取；False 表示无更新，可使用缓存内容
    """
    # 从数据库获取缓存的元数据
    cached_etag = None
    cached_last_modified = None
    if db and db._conn:
        cursor = await db._conn.execute(
            "SELECT etag, last_modified, content FROM channel_cache_raw WHERE url = ?",
            (url,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            cached_etag, cached_last_modified, cached_content = row
            # 如果没有 ETag 和 Last-Modified，则无法判断，需要拉取
            if not cached_etag and not cached_last_modified:
                return True, None, None, None
            # 发送 HEAD 请求检查
            headers = HEADERS.copy()
            if cached_etag:
                headers["If-None-Match"] = cached_etag
            if cached_last_modified:
                headers["If-Modified-Since"] = cached_last_modified
            try:
                async with session.head(url, timeout=10, headers=headers) as resp:
                    if resp.status == 304:
                        return False, cached_content, cached_etag, cached_last_modified
                    else:
                        new_etag = resp.headers.get("ETag", "")
                        new_last_modified = resp.headers.get("Last-Modified", "")
                        return True, None, new_etag, new_last_modified
            except Exception:
                # HEAD 请求失败，回退到 GET
                return True, None, None, None
    return True, None, None, None

async def fetch_url_with_metadata(session: aiohttp.ClientSession, url: str, db):
    """
    智能拉取：先 HEAD 检测，无变化则返回缓存内容；有变化则 GET 并更新缓存。
    返回 content
    """
    # 检查是否修改
    is_modified, cached_content, new_etag, new_last_modified = await check_source_modified(session, url, db)
    if not is_modified and cached_content:
        print(f"✅ 源无变化，使用缓存: {url}")
        return cached_content

    # 需要拉取
    print(f"🔄 源有更新，拉取: {url}")
    attempt = 0
    while True:
        attempt += 1
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as resp:
                if resp.status != 200:
                    raise FetchError(f"HTTP {resp.status}")
                content = await resp.text()
                # 获取响应头中的 ETag 和 Last-Modified
                resp_etag = resp.headers.get("ETag", "")
                resp_last_modified = resp.headers.get("Last-Modified", "")
                # 保存到数据库（如果提供了新值则使用，否则保留旧值）
                if db and db._conn:
                    final_etag = resp_etag or new_etag
                    final_last_modified = resp_last_modified or new_last_modified
                    await db._conn.execute(
                        """INSERT OR REPLACE INTO channel_cache_raw 
                           (url, content, etag, last_modified, updated_at) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (url, content, final_etag, final_last_modified, asyncio.get_event_loop().time())
                    )
                    await db._conn.commit()
                return content
        except Exception as e:
            if not ENABLE_RETRY or attempt >= RETRY_MAX_ATTEMPTS:
                raise FetchError(str(e))
            wait_time = min(RETRY_BACKOFF_FACTOR ** (attempt - 1), RETRY_MAX_WAIT)
            print(f"  重试 {url} ({attempt}/{RETRY_MAX_ATTEMPTS})，等待 {wait_time}s")
            await asyncio.sleep(wait_time)

async def fetch_all_sources_incremental(sources: list, db) -> dict:
    """增量拉取所有源，返回 {url: content} 字典，只包含有变化或首次拉取的内容"""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url_with_metadata(session, url, db) for url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = {}
        for url, res in zip(sources, results):
            if isinstance(res, Exception):
                print(f"⚠️ 拉取失败 {url}: {res}")
                # 尝试从数据库读取旧内容
                if db and db._conn:
                    cursor = await db._conn.execute(
                        "SELECT content FROM channel_cache_raw WHERE url = ?",
                        (url,)
                    )
                    row = await cursor.fetchone()
                    await cursor.close()
                    if row:
                        output[url] = row[0]
                        print(f"📦 使用数据库缓存的旧内容: {url}")
                    else:
                        output[url] = None
                else:
                    output[url] = None
            else:
                output[url] = res
        return output
