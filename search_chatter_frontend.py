import os
import re

search_dir = 'frontend/apps/web/src'
keywords = ['chatter', 'collaboration']

for root, dirs, files in os.walk(search_dir):
    for f in files:
        if f.endswith('.ts') or f.endswith('.vue'):
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                    for i, line in enumerate(lines, 1):
                        if any(kw in line.lower() for kw in keywords):
                            # 跳过注释行
                            stripped = line.strip()
                            if stripped.startswith('//') or stripped.startswith('*'):
                                continue
                            print(f'{filepath}:{i}: {stripped[:120]}')
            except Exception as e:
                pass
