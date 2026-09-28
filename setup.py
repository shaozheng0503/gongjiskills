from setuptools import setup, find_packages

setup(
    name="gongjiskills",
    version="0.2.0",
    description="共绩算力 GPU 弹性部署 CLI / Skills，供 AI Agent 自动调用（零必需依赖）",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    extras_require={"crypto": ["cryptography>=3.0"]},
    package_data={"gongjiskills": ["data/*.json"]},
    entry_points={
        "console_scripts": [
            "gongji=gongjiskills.cli:main",
        ],
    },
)
