"""
RQSM-Engine Package Setup
"""
from setuptools import setup, find_packages

setup(
    name="rqsm-engine",
    version="0.1.0",
    description="Role Queue State Machine Educational Dialogue System",
    author="Capstone Project",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "pydantic>=2.5.3",
        "pdfplumber>=0.10.3",
        "sentence-transformers>=2.3.1",
        "openai>=1.10.0",
        "sqlalchemy>=2.0.25",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "black>=24.1.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
