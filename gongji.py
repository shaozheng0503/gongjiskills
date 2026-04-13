#!/usr/bin/env python3
"""共绩算力 CLI 入口 — 兼容直接运行 python3 gongji.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gongjiskills.cli import main

if __name__ == "__main__":
    main()
