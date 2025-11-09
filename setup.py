from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="automated-assembly-robot",
    version="0.1.0",
    description="自動組立ロボット制御システム - 3Dプリンター、ディスペンサー、XYZ直交ロボットの統合制御",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Assembly Robot Team",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "opencv-python>=4.8.0",
        "aiortc>=1.6.0",
        "aiohttp>=3.9.0",
        "minimalmodbus>=2.1.0",
        "pyserial>=3.5",
        "requests>=2.31.0",
        "RPi.GPIO>=0.7.1",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0.0",
        "numpy>=1.24.0",
        "python-multipart>=0.0.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "assembly-robot=web_app.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Automation",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
