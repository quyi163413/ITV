# src/generator.py
# 输出 M3U 和 TXT 文件模块，严格保持与 demo.txt 相同的顺序

from pathlib import Path
from typing import List, Dict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE
from src.logger import logger

def generate_m3u(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """生成 M3U8 格式文件，保持传入的分类顺序"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            # 写入分类注释行（播放器分组）
            f.write(f'\n#EXTINF:-1 group-title="{cat}",{cat}\n')
            for ch in channels:
                url = ch.get("urls", [ch.get("url")])[0]
                tvg_id = ch.get("id", "")
                tvg_logo = ch.get("logo", "")
                group = ch.get("group_title", cat)
                name = ch["name"]
                extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{group}",{name}'
                f.write(f"{extinf}\n{url}\n")
    logger.info(f"✅ M3U 文件已生成: {output_path}")

def generate_txt(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """生成 TXT 文件，格式与 demo.txt 兼容，保持传入的分类顺序"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            f.write(f"\n{cat},#genre#\n")
            for ch in channels:
                url = ch.get("urls", [ch.get("url")])[0]
                f.write(f"{ch['name']},{url}\n")
    logger.info(f"✅ TXT 文件已生成: {output_path}")

def generate_outputs_from_demo(ordered_channels: List[dict]) -> None:
    """
    ordered_channels 已按照 demo.txt 的顺序排列（包含 demo_category 字段）。
    此函数保持该顺序，按 demo_category 分组后输出 M3U 和 TXT。
    """
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 按 demo_category 分组，保持插入顺序（即 ordered_channels 中首次出现各分类的顺序）
    groups = {}
    for ch in ordered_channels:
        cat = ch.get("demo_category", "其他")
        groups.setdefault(cat, []).append(ch)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_m3u(groups, OUTPUT_DIR / M3U_FILE)
    generate_txt(groups, OUTPUT_DIR / TXT_FILE)
