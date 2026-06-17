# src/demo_filter.py
# Demo 频道筛选与排序模块，支持港澳台日频道自动追加

from pathlib import Path
from typing import List, Tuple
from src.config import DEMO_FILE, OUTPUT_DIR, DEMO_MATCH_MODE
from src.classifier import PROVINCES, classify_channel
from src.logger import logger


def parse_demo_order_with_categories(demo_file: Path = DEMO_FILE) -> List[Tuple[str, str]]:
    """解析 demo.txt，返回 [(分类, 频道名), ...]"""
    if not demo_file.exists():
        logger.warning(f"⚠️ Demo 文件不存在: {demo_file}")
        return []
    
    order = []
    current_category = None
    
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.endswith(",#genre#") or line.endswith(", #genre#"):
                current_category = line.replace(", #genre#", "").replace(", #genre#", "").strip()
                continue
            
            if line.startswith('#'):
                continue
            
            if current_category is not None:
                order.append((current_category, line))
            else:
                order.append(("其他", line))
    
    logger.info(f"📋 从 demo.txt 解析到 {len(order)} 个有序频道")
    
    # 打印前30项
    logger.info("📋 Demo 顺序预览（前30项）：")
    for i, (cat, name) in enumerate(order[:30]):
        marker = " ← CCTV-5+" if name == "CCTV-5+" else ""
        if name == "CCTV-5":
            marker = " ← CCTV-5"
        logger.info(f"   {i+1}. [{cat}] {name}{marker}")
    
    return order


def match_channel_name(channel_name: str, demo_name: str) -> bool:
    """匹配频道名"""
    if DEMO_MATCH_MODE == "exact":
        return channel_name == demo_name
    
    cn_lower = channel_name.lower()
    dn_lower = demo_name.lower()
    
    # CCTV-5+ 匹配
    if dn_lower == "cctv-5+":
        return 'cctv-5+' in cn_lower or 'cctv5+' in cn_lower or 'cctv-5＋' in cn_lower
    
    # CCTV-5 匹配
    if dn_lower == "cctv-5":
        return 'cctv-5' in cn_lower or 'cctv5' in cn_lower or '央视5' in channel_name
    
    # 普通匹配
    return dn_lower in cn_lower or cn_lower in dn_lower


def detect_hmtj_category(name: str) -> str:
    """检测频道属于哪个港澳台日分类"""
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["tvb", "翡翠", "明珠", "无线", "rthk", "hoy", "viu", "香港"]):
        return "香港频道"
    if any(kw in name_lower for kw in ["澳视", "澳门", "macau", "tdm"]):
        return "澳门频道"
    if any(kw in name_lower for kw in ["东森", "民视", "台视", "华视", "中视", "三立", "纬来", "tvbs", "年代", "壹电视", "台湾"]):
        return "台湾频道"
    if any(kw in name_lower for kw in ["nhk", "japan", "tokyo", "fuji", "tbs", "tv asahi", "ntv", "japanese", "日本"]):
        return "日本频道"
    return None


def filter_and_order_by_demo(channels: list) -> tuple:
    """根据 demo.txt 筛选和排序频道，并自动追加未匹配的港澳台日频道"""
    demo_order = parse_demo_order_with_categories()
    if not demo_order:
        logger.warning("⚠️ demo.txt 为空，跳过筛选")
        return channels, []

    name_to_channel = {ch["name"]: ch for ch in channels}
    matched = []
    unmatched = list(channels)
    matched_names = set()
    
    cctv5_matched = False
    cctv5plus_matched = False

    # 第一遍：匹配 demo 中的频道名
    for category, demo_name in demo_order:
        # 精确匹配
        if demo_name in name_to_channel:
            ch = name_to_channel[demo_name].copy()
            ch["demo_category"] = category
            ch["demo_name"] = demo_name
            if ch["name"] not in matched_names:
                matched.append(ch)
                matched_names.add(ch["name"])
                unmatched = [c for c in unmatched if c["name"] != ch["name"]]
                if demo_name == "CCTV-5":
                    cctv5_matched = True
                if demo_name == "CCTV-5+":
                    cctv5plus_matched = True
                continue
        
        # 模糊匹配
        found = False
        for i, ch in enumerate(unmatched[:]):
            if ch["name"] in matched_names:
                continue
            if match_channel_name(ch["name"], demo_name):
                ch_copy = ch.copy()
                ch_copy["demo_category"] = category
                ch_copy["demo_name"] = demo_name
                matched.append(ch_copy)
                matched_names.add(ch["name"])
                unmatched.pop(i)
                found = True
                if demo_name == "CCTV-5":
                    cctv5_matched = True
                    logger.info(f"🎯 匹配到 CCTV-5: {ch['name']}")
                if demo_name == "CCTV-5+":
                    cctv5plus_matched = True
                    logger.info(f"🎯 匹配到 CCTV-5+: {ch['name']}")
                break

    logger.info(f"📊 CCTV-5 匹配: {'成功' if cctv5_matched else '失败'}")
    logger.info(f"📊 CCTV-5+ 匹配: {'成功' if cctv5plus_matched else '失败'}")

    # 第二遍：处理未匹配的港澳台日频道，自动追加
    remaining = []
    hmtj_appended = []
    for ch in unmatched:
        # 判断是否为港澳台日频道
        hmtj_cat = detect_hmtj_category(ch["name"])
        if hmtj_cat:
            ch_copy = ch.copy()
            ch_copy["demo_category"] = hmtj_cat
            ch_copy["demo_name"] = ch["name"]
            hmtj_appended.append(ch_copy)
            matched_names.add(ch["name"])
            logger.info(f"🌏 自动追加港澳台日频道: {ch['name']} -> {hmtj_cat}")
        else:
            remaining.append(ch)
    
    # 将港澳台日频道追加到 matched 后面
    matched.extend(hmtj_appended)
    
    # 剩余未匹配的频道（非港澳台日）
    logger.info(f"🎯 Demo 筛选：原始 {len(channels)} -> 匹配 {len(matched)}，未匹配 {len(remaining)}（其中港澳台日 {len(hmtj_appended)}）")
    
    return matched, remaining


def write_shai_file(unmatched_channels: list, matched_count: int, total_raw: int):
    """保存未匹配的频道列表"""
    shai_path = OUTPUT_DIR / "shai.txt"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(shai_path, "w", encoding="utf-8") as f:
        f.write("# Demo筛选丢弃的频道\n")
        f.write(f"# 原始频道总数: {total_raw}\n")
        f.write(f"# Demo匹配成功: {matched_count}\n")
        f.write(f"# 丢弃数量: {len(unmatched_channels)}\n\n")
        
        for ch in unmatched_channels:
            url = ch["urls"][0] if ch.get("urls") else ch["url"]
            f.write(f"{ch['name']},{url}\n")
    
    logger.info(f"📄 未匹配频道列表已保存: {shai_path}")
