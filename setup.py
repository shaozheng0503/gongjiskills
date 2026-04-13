from setuptools import setup, find_packages

setup(
    name="gongjiskills",
    version="0.1.0",
    description="共绩算力 GPU 弹性部署 CLI / Skills，供 AI Agent 自动调用",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=3.0",
        "requests>=2.20",
    ],
    entry_points={
        "console_scripts": [
            "gongji=gongjiskills.cli:main",
        ],
    },
)
