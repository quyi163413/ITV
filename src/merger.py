# src/merger.py
import re
from collections import defaultdict
from src.config import MAX_SOURCES_PER_CHANNEL, PREFER_H264
from src.logo_matcher import get_logo_matcher
from src.logger import logger

def normalize_channel_name(name: str) -> str:
    """标准化频道名，保留关键符号如 + 和 -"""
    # 去除清晰度标签
    name = re.sub(r'\s*(?:1080[pi]|720[pi]|4K|8K|HD|高清|超清|标清|流畅|付费|备\d*|备用\d*|备播|备源)\s*', '', name, flags=re.IGNORECASE)
    # 去除括号内容
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    # 去除“备用”等字眼
    name = re.sub(r'[备用备播备源]+', '', name)
    # 去除多余空格
    name = re.sub(r'\s+', ' ', name).strip()
    # 重要：不要删除 + 号，CCTV-5+ 保留
    return name

def merge_channels_by_name(valid_channels: list) -> list:
    groups = defaultdict(list)
    for ch in valid_channels:
        raw_name = ch["name"]
        # 特殊处理 CCTV-5+ / CCTV5+，避免与 CCTV-5 合并
        if re.search(r'CCTV[-\s]*5\s*[＋\+]', raw_name, re.IGNORECASE):
            norm_name = "CCTV-5+"
        else:
            norm_name = normalize_channel_name(raw_name)
        groups[norm_name].append(ch)

    logo_matcher = get_logo_matcher()
    matched_logos = 0
    
    merged = []
    for norm_name, ch_list in groups.items():
        # 排序：优先 H.264，然后延迟低
        def sort_key(ch):
            codec = ch.get("video_codec", "").lower()
            if codec == "h264":
                codec_priority = 0
            elif codec in ["hevc", "h265"]:
                codec_priority = 1
            else:
                codec_priority = 2
            latency = ch.get("latency", 9999)
            return (codec_priority, latency)
        ch_list.sort(key=sort_key)
        top = ch_list[:MAX_SOURCES_PER_CHANNEL]
        primary = top[0]
        
        # 最终频道名使用标准化名称（但保留 +）
        channel_name = norm_name
        # 如果是 CCTV-5+ 且原始名中可能有差异，统一为 "CCTV-5+"
        if norm_name == "CCTV-5+" and not channel_name.endswith('+'):
            channel_name = "CCTV-5+"
        
        logo_url = primary.get("tvg_logo", "")
        if not logo_url:
            logo_url = logo_matcher.get_logo_url(channel_name)
            matched_logos += 1
        
        merged_ch = {
            "name": channel_name,
            "urls": [c["url"] for c in top],
            "url": primary["url"],
            "latency": primary["latency"],
            "video_codec": primary["video_codec"],
            "group_title": primary.get("group_title", ""),
            "id": primary.get("tvg_id", ""),
            "logo": logo_url,
        }
        merged.append(merged_ch)
    
    logger.info(f"🔄 频道合并完成：{len(valid_channels)} 个源 -> {len(merged)} 个频道")
    logger.info(f"🖼️ 图标匹配：为 {matched_logos} 个频道自动匹配了图标")
    return merged
