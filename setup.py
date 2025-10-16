"""
Lolo Trading Agent - AI-Powered Multi-Agent Trading System
Setup configuration for package installation
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lolo-trading-agent",
    version="1.0.0",
    author="Lolo Trading Team",
    author_email="contact@lolotrading.com",
    description="AI-Powered Multi-Agent Trading System for MetaTrader 5",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Q-alduaij/Lolo-Trading-Agent-",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "python-dotenv>=1.0.0",
        "MetaTrader5>=5.0.45",
        "langchain>=0.1.0",
        "langgraph>=0.0.20",
        "openai>=1.10.0",
        "chromadb>=0.4.22",
        "Flask>=3.0.0",
        "Flask-Login>=0.6.3",
        "Flask-WTF>=1.2.1",
        "Flask-SocketIO>=5.3.5",
        "SQLAlchemy>=2.0.25",
        "pandas>=2.1.4",
        "numpy>=1.26.3",
        "pandas-ta>=0.3.14b0",
        "requests>=2.31.0",
        "plotly>=5.18.0",
        "APScheduler>=3.10.4",
        "pytz>=2023.3",
    ],
    entry_points={
        "console_scripts": [
            "lolo-trading-agent=main:main",
        ],
    },
)

