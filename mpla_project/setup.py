from setuptools import setup, find_packages

setup(
    name="mpla",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-dotenv",
        "google-generativeai",
        "typer[all]",
        "pydantic",
        "openai",
        "aiosqlite",
        "httpx",
        "PyYAML",
        "loguru",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
        ],
    },
    entry_points={
        'console_scripts': [
            'mpla-cli = mpla.cli:app',
        ],
    },
) 