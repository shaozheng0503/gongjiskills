#!/usr/bin/env python3
"""共绩算力 CLI 兼容入口

三种运行方式等价：
    gongji <cmd>                      # pip install 后
    python -m gongjiskills <cmd>      # 无需安装，仓库内直接跑
    python gongji.py <cmd>            # 兼容旧入口
"""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gongjiskills.cli import main

if __name__ == "__main__":
    main()
