# src/speed_tester.py - 增强版，过滤广告和无效源

import asyncio
import aiohttp
import time
import re
from tqdm.asyncio import tqdm
from src.config import HEADERS, TIMEOUT, MAX_WORKERS
from src.database import get_db_cache, channel_key
from src.logger import logger

# 广告/追踪域名黑名单
AD_PATTERNS = [
    r'ads?\.',
    r'adserver',
    r'doubleclick',
    r'googlead',
    r'googlesyndication',
    r'amazon-adsystem',
    r'criteo',
    r'taboola',
    r'outbrain',
    r'scorecardresearch',
    r'moatads',
    r'openx',
    r'pubmatic',
    r'/ad/',
    r'/ads/',
    r'/sponsor',
    r'/promo',
]

# 无效内容关键词（响应体中包含则视为无效）
INVALID_CONTENT_PATTERNS = [
    r'<html',
    r'<!DOCTYPE',
    r'404 not found',
    r'access denied',
    r'forbidden',
    r'请勿滥用',
    r'该资源暂不可用',
]

def is_suspicious_url(url: str) -> bool:
    """检查URL是否可能为广告/追踪链接"""
    url_lower = url.lower()
    for pattern in AD_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False

async def probe_channel_robust(session: aiohttp.ClientSession, channel: dict) -> tuple:
    """增强探测：HEAD + 少量数据验证，过滤广告和无效源"""
    url = channel["url"]
    
    # 快速URL过滤
    if is_suspicious_url(url):
        logger.debug(f"🚫 广告URL过滤: {url[:100]}")
        return channel, 0, False, None
    
    try:
        start = time.time()
        
        # 先尝试 HEAD 请求
        async with session.head(url, timeout=5, allow_redirects=True, headers=HEADERS) as resp:
            if resp.status != 200:
                return channel, 0, False, None
            
            content_type = resp.headers.get("content-type", "").lower()
            if "video" not in content_type and "mpegurl" not in content_type and "x-mpegurl" not in content_type:
                return channel, 0, False, None
        
        latency = int((time.time() - start) * 1000)
        
        # 再取少量数据验证（只验证前16KB）
        try:
            async with session.get(url, timeout=8, headers={**HEADERS, "Range": "bytes=0-16384"}) as resp:
                if resp.status not in [200, 206]:
                    return channel, latency, False, None
                
                data = await resp.content.read(16384)
                
                # 检查是否为HTML页面
                data_lower = data.lower()
                for pattern in INVALID_CONTENT_PATTERNS:
                    if re.search(pattern.encode(), data_lower):
                        return channel, latency, False, None
                
                # 检查是否为有效的M3U8或视频流
                if data.startswith(b'#EXTM3U') or b'#EXTINF' in data:
                    return channel, latency, True, None
                
                # 检查视频文件头
                video_signatures = [
                    b'\x00\x00\x00\x18ftyp',  # MP4
                    b'\x00\x00\x00\x1cftyp',  # MP4
                    b'\x1a\x45\xdf\xa3',      # MKV
                    b'\x47\x40\x00',          # TS
                    b'FLV',                   # FLV
                ]
                for sig in video_signatures:
                    if data.startswith(sig):
                        return channel, latency, True, None
                
                # 无法确认视频格式
                return channel, latency, False, None
                
        except asyncio.TimeoutError:
            return channel, latency, False, None
        except Exception:
            return channel, latency, False, None
            
    except asyncio.TimeoutError:
        return channel, 0, False, None
    except Exception:
        return channel, 0, False, None

async def test_channels_concurrent(channels_dict: dict) -> list:
    """并发测速，返回有效的频道列表"""
    channels = list(channels_dict.values())
    db = await get_db_cache()
    
    # 缓存读取
    cached_results = []
    to_probe = []
    for ch in channels:
        key = channel_key(ch["name"], ch["url"])
        cached = await db.get_speed_result(key)
        if cached and cached.get("latency", 9999) < 9999:
            ch["latency"] = cached["latency"]
            ch["video_codec"] = cached.get("video_codec", "")
            cached_results.append(ch)
        else:
            to_probe.append(ch)
    
    logger.info(f"⚡ 测速: {len(to_probe)} 个新频道需探测，{len(cached_results)} 个来自缓存")
    
    valid = cached_results.copy()
    
    if to_probe:
        semaphore = asyncio.Semaphore(MAX_WORKERS)
        
        async def bounded_probe(session, ch):
            async with semaphore:
                return await probe_channel_robust(session, ch)
        
        connector = aiohttp.TCPConnector(limit=MAX_WORKERS, limit_per_host=5)
        timeout_config = aiohttp.ClientTimeout(total=TIMEOUT + 5)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout_config) as session:
            tasks = [bounded_probe(session, ch) for ch in to_probe]
            
            for coro in tqdm.as_completed(tasks, desc="🔍 测速+过滤", unit="频道", total=len(tasks), leave=True):
                ch, latency, ok, _ = await coro
                if ok:
                    ch["latency"] = latency
                    valid.append(ch)
                    key = channel_key(ch["name"], ch["url"])
                    await db.set_speed_result(key, ch)
    
    # 按延迟排序
    valid.sort(key=lambda x: x.get("latency", 9999))
    
    # 统计过滤效果
    total = len(channels)
    filtered = total - len(valid)
    logger.info(f"✅ 测速完成: 有效 {len(valid)}/{total}，过滤 {filtered} 个无效/广告源")
    
    return valid
