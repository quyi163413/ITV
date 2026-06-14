# src/special_categories.py
"""特殊分类采集模块 - 从指定源提取特色分类内容"""

import re
from typing import List, Dict, Tuple
from pathlib import Path

from src.logger import logger

# 需要采集的特殊分类关键词
SPECIAL_CATEGORIES = [
    "每日电影",
    "经典电影", 
    "热门歌曲",
    "韩国女团",
    "动感舞曲",
    "戏曲频道",
    "网络电台"
]

# 分类的中文显示名称映射
CATEGORY_DISPLAY_NAME = {
    "每日电影": "🎬 每日电影",
    "经典电影": "🎬 经典电影",
    "热门歌曲": "🎵 热门歌曲",
    "韩国女团": "🎤 韩国女团",
    "动感舞曲": "🎧 动感舞曲",
    "戏曲频道": "🎭 戏曲频道",
    "网络电台": "📻 网络电台",
}


def parse_special_categories(content: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    从源内容中解析特殊分类
    返回: {分类名: [(频道名, URL), ...]}
    """
    if not content:
        return {}
    
    result = {cat: [] for cat in SPECIAL_CATEGORIES}
    lines = content.splitlines()
    
    current_category = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检测分类行（格式：分类名,#genre#）
        if line.endswith(",#genre#"):
            cat_name = line.replace(",#genre#", "").strip()
            # 检查是否是我们要采集的分类
            for special_cat in SPECIAL_CATEGORIES:
                if special_cat in cat_name:
                    current_category = special_cat
                    break
                # 也检查常见的变体
                if cat_name in ["抖音直播", "music", "音乐"] and special_cat in ["热门歌曲", "韩国女团", "动感舞曲"]:
                    current_category = special_cat
            continue
        
        # 跳过注释行
        if line.startswith('#'):
            continue
        
        # 解析频道行（格式：频道名,URL）
        if ',' in line and current_category and current_category in result:
            parts = line.split(',', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith(('http://', 'https://')):
                    result[current_category].append((name, url))
    
    # 过滤空分类并去重
    for cat in result:
        if result[cat]:
            # 去重（基于URL）
            seen_urls = set()
            unique = []
            for name, url in result[cat]:
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique.append((name, url))
            result[cat] = unique
            logger.info(f"📁 解析到 {cat}: {len(result[cat])} 个频道")
    
    return {k: v for k, v in result.items() if v}


async def fetch_special_categories_source(db=None) -> Dict[str, List[Tuple[str, str]]]:
    """
    获取特殊分类源并解析
    """
    from src.fetcher import fetch_url_with_metadata
    import aiohttp
    
    source_url = "https://tv.19860519.xyz/abc123"
    
    try:
        async with aiohttp.ClientSession() as session:
            db_for_fetch = db
            content = await fetch_url_with_metadata(session, source_url, db_for_fetch)
            if content:
                return parse_special_categories(content)
            else:
                logger.warning(f"⚠️ 无法获取特殊分类源: {source_url}")
                return {}
    except Exception as e:
        logger.error(f"❌ 获取特殊分类源失败: {e}")
        return {}


def append_special_categories_to_m3u(
    special_data: Dict[str, List[Tuple[str, str]]],
    output_path: Path,
    existing_count: int = 0
) -> int:
    """将特殊分类追加到现有的 M3U 文件末尾"""
    if not special_data:
        return 0
    
    total_appended = 0
    
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write(f"\n# ========== 特色分类内容（共 {sum(len(v) for v in special_data.values())} 个频道） ==========\n")
        
        for cat in SPECIAL_CATEGORIES:
            channels = special_data.get(cat, [])
            if not channels:
                continue
            
            display_name = CATEGORY_DISPLAY_NAME.get(cat, cat)
            f.write(f"\n# ----- {display_name} ({len(channels)}个频道) -----\n")
            
            for name, url in channels:
                f.write(f'#EXTINF:-1 group-title="{display_name}",{name}\n{url}\n')
                total_appended += 1
    
    logger.info(f"✅ 已将 {total_appended} 个特色频道追加到 M3U: {output_path}")
    return total_appended


def append_special_categories_to_txt(
    special_data: Dict[str, List[Tuple[str, str]]],
    output_path: Path
) -> int:
    """将特殊分类追加到现有的 TXT 文件末尾"""
    if not special_data:
        return 0
    
    total_appended = 0
    
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write(f"\n# ========== 特色分类内容 ==========\n")
        
        for cat in SPECIAL_CATEGORIES:
            channels = special_data.get(cat, [])
            if not channels:
                continue
            
            display_name = CATEGORY_DISPLAY_NAME.get(cat, cat)
            f.write(f"\n{display_name},#genre#\n")
            
            for name, url in channels:
                f.write(f"{name},{url}\n")
                total_appended += 1
    
    logger.info(f"✅ 已将 {total_appended} 个特色频道追加到 TXT: {output_path}")
    return total_appended


async def collect_and_append_special_categories(output_dir: Path, db=None) -> Dict[str, int]:
    """
    主函数：采集特殊分类并追加到输出文件
    返回统计信息
    """
    logger.info("🎬 开始采集特色分类内容...")
    
    # 获取数据
    special_data = await fetch_special_categories_source(db)
    
    if not special_data:
        logger.warning("⚠️ 未获取到任何特色分类内容")
        return {}
    
    # 统计
    stats = {cat: len(channels) for cat, channels in special_data.items()}
    total = sum(stats.values())
    logger.info(f"📊 特色分类统计: 共 {total} 个频道")
    for cat, count in stats.items():
        logger.info(f"   {cat}: {count}")
    
    # 追加到输出文件
    m3u_path = output_dir / "tv.m3u"
    txt_path = output_dir / "tv.txt"
    
    m3u_count = append_special_categories_to_m3u(special_data, m3u_path)
    txt_count = append_special_categories_to_txt(special_data, txt_path)
    
    # 也追加到 EPG 版本（如果存在）
    epg_path = output_dir / "tv_epg.m3u"
    if epg_path.exists():
        append_special_categories_to_m3u(special_data, epg_path)
    
    # 也追加到精简版（如果存在）
    lite_path = output_dir / "tv_lite.m3u"
    if lite_path.exists():
        append_special_categories_to_m3u(special_data, lite_path)
    
    return stats
