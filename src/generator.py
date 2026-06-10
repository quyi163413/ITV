# src/generator.py
# 输出 M3U 和 TXT 文件模块，按央视频道顺序 + demo.txt 顺序输出

from pathlib import Path
from typing import List, Dict, Tuple
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE, CCTV_ORDER
from src.logger import logger

def get_cctv_order_index(name: str) -> int:
    """获取央视频道在 CCTV_ORDER 中的索引，非央视返回 -1"""
    name_lower = name.lower()
    for idx, std in enumerate(CCTV_ORDER):
        if std.lower() == name_lower or name_lower.startswith(std.lower()):
            return idx
    return -1

def sort_channels_by_demo_order(channels: List[dict], demo_order: List[Tuple[str, str]] = None) -> List[dict]:
    """
    排序规则：
    1. 央视频道：按 CCTV_ORDER 顺序（1,2,3,...）
    2. 其他频道：按 demo.txt 中出现的顺序，若不在 demo 中则按名称排序
    """
    if demo_order is None:
        demo_order = []
    
    # 构建 demo 顺序映射（仅用于非央视）
    demo_index = {demo_name: idx for idx, (_, demo_name) in enumerate(demo_order)} if demo_order else {}
    
    def sort_key(ch):
        name = ch["name"]
        cctv_idx = get_cctv_order_index(name)
        if cctv_idx >= 0:
            # 央视频道：优先级 0，按 CCTV_ORDER 索引排序
            return (0, cctv_idx, name)
        else:
            # 非央视频道：优先级 1，按 demo 顺序，若无则按名称
            idx = demo_index.get(name, len(demo_index)) if demo_index else 0
            return (1, idx, name)
    
    return sorted(channels, key=sort_key)

def generate_m3u(channels_by_category: Dict[str, List[dict]], output_path: Path, demo_order: List[Tuple[str, str]] = None) -> None:
    """生成标准 M3U8 格式文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            
            # 按规则排序
            channels = sort_channels_by_demo_order(channels, demo_order)
            
            for ch in channels:
                url = ch.get("urls", [ch.get("url")])[0]
                name = ch["name"]
                extinf = f'#EXTINF:-1 group-title="{cat}",{name}'
                f.write(f"{extinf}\n{url}\n")
    
    logger.info(f"✅ M3U 文件已生成: {output_path}")

def generate_txt(channels_by_category: Dict[str, List[dict]], output_path: Path, demo_order: List[Tuple[str, str]] = None) -> None:
    """生成 TXT 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            
            channels = sort_channels_by_demo_order(channels, demo_order)
            
            f.write(f"\n{cat},#genre#\n")
            for ch in channels:
                url = ch.get("urls", [ch.get("url")])[0]
                f.write(f"{ch['name']},{url}\n")
    
    logger.info(f"✅ TXT 文件已生成: {output_path}")

def generate_outputs_from_demo(ordered_channels: List[dict], demo_order: List[Tuple[str, str]] = None) -> None:
    """输出 M3U 和 TXT 文件"""
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 按 demo_category 分组
    groups = {}
    for ch in ordered_channels:
        cat = ch.get("demo_category", "其他")
        groups.setdefault(cat, []).append(ch)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_m3u(groups, OUTPUT_DIR / M3U_FILE, demo_order)
    generate_txt(groups, OUTPUT_DIR / TXT_FILE, demo_order)
    
    # 生成多源 M3U（支持自动切换）
    with open(OUTPUT_DIR / "tv_multi.m3u", 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for cat, channels in groups.items():
            channels = sort_channels_by_demo_order(channels, demo_order)
            for ch in channels:
                urls = ch.get("urls", [ch.get("url")])
                multi_url = " # ".join(urls)
                f.write(f'#EXTINF:-1 group-title="{cat}",{ch["name"]}\n{multi_url}\n')
    
    logger.info(f"✅ 多源 M3U 文件已生成: {OUTPUT_DIR / 'tv_multi.m3u'}")
