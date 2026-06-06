# src/generator.py
# 输出 M3U 和 TXT 文件模块，严格保持 demo.txt 的顺序

from pathlib import Path
from typing import List, Dict, Tuple
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE
from src.logger import logger
from src.demo_filter import parse_demo_order_with_categories

def generate_m3u(channels_by_category: Dict[str, List[dict]], 
                 demo_order: List[Tuple[str, str]], 
                 output_path: Path) -> None:
    """
    生成 M3U8 格式文件，严格按照 demo.txt 的分类和频道顺序
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        
        # 记录已经处理过的分类，避免重复
        processed_categories = set()
        
        # 按照 demo.txt 的顺序遍历分类
        for category, demo_channel_name in demo_order:
            if category in processed_categories:
                continue
            # 如果这个分类在 channels_by_category 中存在
            if category in channels_by_category:
                channels = channels_by_category[category]
                if channels:
                    # 写入分类注释行
                    f.write(f'\n#EXTINF:-1 group-title="{category}",{category}\n')
                    
                    # 按照 demo.txt 中该分类下的频道顺序输出
                    # 先收集该分类下在 demo 中有序的频道
                    ordered_in_category = []
                    remaining_in_category = []
                    
                    # 创建一个 name -> channel 的映射
                    name_to_ch = {ch["name"]: ch for ch in channels}
                    
                    # 按照 demo 中的顺序添加频道
                    for _, demo_name in demo_order:
                        if demo_name in name_to_ch:
                            ordered_in_category.append(name_to_ch[demo_name])
                            name_to_ch.pop(demo_name)
                    
                    # 添加该分类下 demo 中没有的频道（放在最后）
                    remaining_in_category = list(name_to_ch.values())
                    
                    # 合并：先 demo 顺序，后剩余的（按名称排序）
                    all_channels_in_cat = ordered_in_category + sorted(remaining_in_category, key=lambda x: x["name"])
                    
                    for ch in all_channels_in_cat:
                        url = ch.get("urls", [ch.get("url")])[0]
                        tvg_id = ch.get("id", "")
                        tvg_logo = ch.get("logo", "")
                        group = ch.get("group_title", category)
                        name = ch["name"]
                        extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{group}",{name}'
                        f.write(f"{extinf}\n{url}\n")
                
                processed_categories.add(category)
        
        # 处理 demo.txt 中没有但实际存在的分类（放在最后）
        for category, channels in channels_by_category.items():
            if category not in processed_categories and channels:
                f.write(f'\n#EXTINF:-1 group-title="{category}",{category}\n')
                for ch in channels:
                    url = ch.get("urls", [ch.get("url")])[0]
                    tvg_id = ch.get("id", "")
                    tvg_logo = ch.get("logo", "")
                    group = ch.get("group_title", category)
                    name = ch["name"]
                    extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{group}",{name}'
                    f.write(f"{extinf}\n{url}\n")
    
    logger.info(f"✅ M3U 文件已生成（按 demo.txt 顺序）: {output_path}")

def generate_txt(channels_by_category: Dict[str, List[dict]], 
                 demo_order: List[Tuple[str, str]], 
                 output_path: Path) -> None:
    """
    生成 TXT 文件，格式与 demo.txt 兼容，严格保持顺序
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        processed_categories = set()
        
        # 按照 demo.txt 的顺序遍历
        for category, demo_channel_name in demo_order:
            if category in processed_categories:
                continue
            if category in channels_by_category:
                channels = channels_by_category[category]
                if channels:
                    f.write(f"\n{category},#genre#\n")
                    
                    # 按照 demo 顺序输出该分类下的频道
                    name_to_ch = {ch["name"]: ch for ch in channels}
                    
                    # 先写 demo 中存在的
                    for _, demo_name in demo_order:
                        if demo_name in name_to_ch:
                            url = name_to_ch[demo_name].get("urls", [name_to_ch[demo_name].get("url")])[0]
                            f.write(f"{demo_name},{url}\n")
                            name_to_ch.pop(demo_name)
                    
                    # 再写 demo 中不存在的（按名称排序）
                    for ch in sorted(name_to_ch.values(), key=lambda x: x["name"]):
                        url = ch.get("urls", [ch.get("url")])[0]
                        f.write(f"{ch['name']},{url}\n")
                
                processed_categories.add(category)
        
        # 处理 demo.txt 中没有的分类
        for category, channels in channels_by_category.items():
            if category not in processed_categories and channels:
                f.write(f"\n{category},#genre#\n")
                for ch in channels:
                    url = ch.get("urls", [ch.get("url")])[0]
                    f.write(f"{ch['name']},{url}\n")
    
    logger.info(f"✅ TXT 文件已生成（按 demo.txt 顺序）: {output_path}")

def generate_outputs_from_demo(ordered_channels: List[dict]) -> None:
    """
    ordered_channels 已按照 demo.txt 的顺序排列（包含 demo_category 字段）。
    此函数保持该顺序，按 demo_category 分组后输出 M3U 和 TXT。
    """
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 按 demo_category 分组
    groups = {}
    for ch in ordered_channels:
        cat = ch.get("demo_category", "其他")
        groups.setdefault(cat, []).append(ch)

    # 获取 demo.txt 的顺序
    demo_order = parse_demo_order_with_categories()
    if not demo_order:
        logger.warning("demo.txt 为空，无法保持顺序，将按分类名排序")
        # 降级方案：按分类名排序
        sorted_cats = sorted(groups.keys())
        final_groups = {cat: groups[cat] for cat in sorted_cats}
    else:
        # demo_order 已经包含了所有分类和频道的顺序
        # 我们只需要按分类顺序输出即可，频道顺序在 generate 函数内部处理
        final_groups = groups

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_m3u(final_groups, demo_order, OUTPUT_DIR / M3U_FILE)
    generate_txt(final_groups, demo_order, OUTPUT_DIR / TXT_FILE)
