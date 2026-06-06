# src/blacklist_filter.py
# URL 黑名单过滤器

import re
from pathlib import Path
from typing import List, Union
from src.config import BLACKLIST_FILE

class BlacklistFilter:
    def __init__(self, blacklist_file: Path = BLACKLIST_FILE):
        self.patterns: List[Union[str, re.Pattern]] = []
        self._load(blacklist_file)
    
    def _load(self, filepath):
        if not filepath.exists():
            print(f"⚠️ 黑名单文件不存在: {filepath}")
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if re.search(r'[\.\*\?\+\[\]\(\)\{\}\\]', line):
                    try:
                        self.patterns.append(re.compile(line, re.IGNORECASE))
                    except re.error as e:
                        print(f"⚠️ 正则错误: {line} -> {e}")
                else:
                    self.patterns.append(line.lower())
        print(f"✅ 已加载 {len(self.patterns)} 条黑名单规则")
    
    def is_blacklisted(self, url: str) -> bool:
        url_lower = url.lower()
        for p in self.patterns:
            if isinstance(p, re.Pattern):
                if p.search(url):
                    return True
            else:
                if p in url_lower:
                    return True
        return False
    
    def filter_channels(self, channels: list) -> list:
        original = len(channels)
        filtered = [ch for ch in channels if not self.is_blacklisted(ch["url"])]
        print(f"🛡️ 黑名单过滤：{original} -> {len(filtered)} 个频道")
        return filtered

_filter = None

def get_blacklist_filter():
    global _filter
    if _filter is None:
        _filter = BlacklistFilter()
    return _filter
