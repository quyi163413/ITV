# src/speed_tester.py - 增强版，更准确的测速和过滤，优化进度条显示

import asyncio
import aiohttp
import time
import re
import sys
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

# 无效内容关键词
INVALID_CONTENT_PATTERNS = [
    r'<html',
    r'<!DOCTYPE',
    r'404 not found',
    r'access denied',
    r'forbidden',
    r'请勿滥用',
    r'该资源暂不可用',
    r'live\.twitch\.tv/embed',
    r'youtube\.com',
]


def is_suspicious_url(url: str) -> bool:
    """检查URL是否可能为广告/追踪链接"""
    url_lower = url.lower()
    for pattern in AD_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False


async def probe_channel_advanced(session: aiohttp.ClientSession, channel: dict, semaphore: asyncio.Semaphore) -> tuple:
    """
    增强探测：HEAD + 分段下载测试，获取更准确的延迟和码率信息
    返回 (channel, latency, is_valid, speed)
    """
    async with semaphore:
        url = channel["url"]
        
        # 快速URL过滤
        if is_suspicious_url(url):
            return channel, 0, False, 0
        
        try:
            start = time.time()
            
            # 1. 先尝试 HEAD 请求
            try:
                async with session.head(url, timeout=5, allow_redirects=True, headers=HEADERS) as resp:
                    if resp.status != 200:
                        return channel, 0, False, 0
                    
                    content_type = resp.headers.get("content-type", "").lower()
                    if "video" not in content_type and "mpegurl" not in content_type and "x-mpegurl" not in content_type:
                        return channel, 0, False, 0
            except:
                return channel, 0, False, 0
            
            head_latency = int((time.time() - start) * 1000)
            
            # 2. 下载一小段数据测试实际速度（下载前256KB）
            start_download = time.time()
            downloaded = 0
            try:
                async with session.get(url, timeout=TIMEOUT, headers={**HEADERS, "Range": "bytes=0-262144"}) as resp:
                    if resp.status not in [200, 206]:
                        return channel, head_latency, False, 0
                    
                    data = await resp.content.read(262144)
                    downloaded = len(data)
                    
                    # 检查是否为HTML页面
                    data_lower = data.lower()
                    for pattern in INVALID_CONTENT_PATTERNS:
                        if re.search(pattern.encode(), data_lower):
                            return channel, head_latency, False, 0
                    
                    # 检查是否为有效的M3U8或视频流
                    is_valid = False
                    if data.startswith(b'#EXTM3U') or b'#EXTINF' in data:
                        is_valid = True
                    else:
                        # 检查视频文件头
                        video_signatures = [
                            b'\x00\x00\x00\x18ftyp', b'\x00\x00\x00\x1cftyp',
                            b'\x1a\x45\xdf\xa3',
                            b'\x47\x40\x00',
                            b'FLV',
                        ]
                        for sig in video_signatures:
                            if data.startswith(sig):
                                is_valid = True
                                break
                    
                    if not is_valid:
                        return channel, head_latency, False, 0
                    
                    # 计算下载速度 (KB/s)
                    download_time = time.time() - start_download
                    speed = downloaded / download_time / 1024 if download_time > 0 else 0
                    
                    # 最终延迟 = HEAD延迟 + 下载延迟的一部分
                    final_latency = head_latency + int(download_time * 1000)
                    
                    return channel, final_latency, True, speed
                    
            except asyncio.TimeoutError:
                return channel, head_latency, False, 0
            except Exception:
                return channel, head_latency, False, 0
                
        except asyncio.TimeoutError:
            return channel, 0, False, 0
        except Exception:
            return channel, 0, False, 0


async def test_channels_concurrent(channels_dict: dict) -> list:
    """并发测速，返回有效的频道列表（按延迟和质量排序）"""
    channels = list(channels_dict.values())
    db = await get_db_cache()
    
    # 缓存读取
    cached_results = []
    to_probe = []
    for ch in channels:
        key = channel_key(ch["name"], ch["url"])
        cached = await db.get_speed_result(key)
        if cached and cached.get("latency", 9999) < 5000:
            ch["latency"] = cached["latency"]
            ch["video_codec"] = cached.get("video_codec", "")
            ch["speed"] = cached.get("speed", 0)
            cached_results.append(ch)
        else:
            to_probe.append(ch)
    
    logger.info(f"⚡ 测速: {len(to_probe)} 个新频道需探测，{len(cached_results)} 个来自缓存")
    
    valid = cached_results.copy()
    
    if to_probe:
        semaphore = asyncio.Semaphore(MAX_WORKERS)
        connector = aiohttp.TCPConnector(limit=MAX_WORKERS, limit_per_host=3)
        timeout_config = aiohttp.ClientTimeout(total=TIMEOUT + 5)
        
        # 使用 tqdm 但禁用默认输出，手动控制进度条
        pbar = tqdm(
            total=len(to_probe), 
            desc="🔍 测速+过滤", 
            unit="频道",
            ncols=80,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            position=0,
            leave=True
        )
        
        completed = 0
        valid_found = 0
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout_config) as session:
            # 创建所有任务但不使用 as_completed（因为它会频繁刷新）
            tasks = []
            for ch in to_probe:
                task = asyncio.create_task(probe_channel_advanced(session, ch, semaphore))
                tasks.append((ch, task))
            
            # 逐个等待任务完成，更新进度条
            for ch, task in tasks:
                result_ch, latency, ok, speed = await task
                completed += 1
                
                if ok:
                    result_ch["latency"] = latency
                    result_ch["speed"] = speed
                    valid.append(result_ch)
                    valid_found += 1
                    key = channel_key(result_ch["name"], result_ch["url"])
                    await db.set_speed_result(key, result_ch)
                
                # 更新进度条描述（显示当前有效数量）
                pbar.set_description(f"🔍 测速+过滤 (有效:{valid_found})")
                pbar.update(1)
        
        pbar.close()
    
    # 按质量排序：延迟优先，速度次之
    def sort_key(ch):
        latency = ch.get("latency", 9999)
        speed = ch.get("speed", 0)
        return (latency, -speed)
    
    valid.sort(key=sort_key)
    
    # 统计过滤效果
    total = len(channels)
    filtered = total - len(valid)
    
    # 输出延迟统计
    if valid:
        latencies = [ch.get("latency", 9999) for ch in valid[:100]]
        avg_latency = sum(latencies) / len(latencies)
        logger.info(f"✅ 测速完成: 有效 {len(valid)}/{total}，过滤 {filtered} 个无效源")
        logger.info(f"📊 平均延迟: {avg_latency:.0f}ms (前100个频道)")
    
    return valid
