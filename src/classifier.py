# src/classifier.py
# 智能分类模块：央视、卫视、地方、港澳台，并提取地方子分类

from src.config import CCTV_ORDER

# 完整的省份/直辖市/自治区列表（用于识别）
PROVINCES = [
    "北京", "天津", "上海", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "海南", "四川",
    "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
    "内蒙古", "广西", "西藏", "宁夏", "新疆",
    "香港", "澳门"
]

# 港澳台关键词
HK_MACAU_TAIWAN_KEYWORDS = [
    "港", "澳", "台", "香港", "澳门", "台湾", "翡翠", "明珠", "凤凰", "tvb", "无线",
    "rthk", "hoy", "viu", "tvbs", "东森", "民视", "台视", "华视", "中视", "三立",
    "纬来", "靖天", "星空", "澳视", "澳门卫视", "香港卫视", "凤凰卫视", "TVB"
]

def classify_channel(channel: dict) -> str:
    name = channel.get("name", "")
    name_lower = name.lower()
    group = channel.get("group_title", "").lower()
    
    # 1. 央视
    if any(kw in name_lower for kw in ["cctv", "央视", "中央电视", "中央-", "中央台", "cntv"]):
        return "央视"
    
    # 2. 港澳台（优先级高于卫视和地方）
    for kw in HK_MACAU_TAIWAN_KEYWORDS:
        if kw.lower() in name_lower or kw.lower() in group:
            return "港澳台"
    
    # 3. 卫视
    if "卫视" in name:
        return "卫视"
    
    # 4. 地方
    for prov in PROVINCES:
        if prov in name:
            return "地方"
    if any(kw in name for kw in ["电视台", "综合频道", "公共频道", "生活频道", "新闻综合"]):
        return "地方"
    
    return "其他"

def extract_subcategory(channel: dict) -> str:
    """提取地方频道的子分类（如“北京频道”）"""
    name = channel.get("name", "")
    group = channel.get("group_title", "")
    
    # 优先从频道名中提取省份
    for prov in PROVINCES:
        if prov in name:
            return f"{prov}频道"
    # 其次从 group_title 中提取
    for prov in PROVINCES:
        if prov in group:
            return f"{prov}频道"
    # 若都没有，返回“地方频道”
    return "地方频道"

def classify_and_filter(channels: list) -> dict:
    """只保留央视、卫视、地方、港澳台四类，并为地方频道添加 subcategory 字段"""
    result = {"央视": [], "卫视": [], "地方": [], "港澳台": []}
    other_count = 0
    for ch in channels:
        cat = classify_channel(ch)
        if cat in result:
            if cat == "地方":
                ch["subcategory"] = extract_subcategory(ch)
            result[cat].append(ch)
        else:
            other_count += 1
    
    # 央视频道排序
    if result["央视"]:
        def ctv_key(ch):
            name = ch["name"]
            for idx, std in enumerate(CCTV_ORDER):
                if std.lower() == name.lower() or name.lower().startswith(std.lower()):
                    return idx
            return len(CCTV_ORDER)
        result["央视"].sort(key=ctv_key)
    
    # 其他分类按名称排序
    for cat in ["卫视", "地方", "港澳台"]:
        if result[cat]:
            result[cat].sort(key=lambda x: x["name"])
    
    print("📊 分类统计（央视/卫视/地方/港澳台）：")
    for cat, lst in result.items():
        if lst:
            print(f"  {cat}: {len(lst)} 个频道")
            if cat == "地方":
                subcats = {}
                for ch in lst:
                    sub = ch.get("subcategory", "地方频道")
                    subcats[sub] = subcats.get(sub, 0) + 1
                for sub, cnt in subcats.items():
                    print(f"    - {sub}: {cnt}")
    print(f"  （其他分类被过滤: {other_count} 个频道）")
    return result
