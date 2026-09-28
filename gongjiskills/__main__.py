"""python -m gongjiskills 入口 — 无需 pip install 即可运行

用法: python -m gongjiskills <命令> [参数]
等价于安装后的 gongji 命令。
"""

from .cli import main

if __name__ == "__main__":
    main()
