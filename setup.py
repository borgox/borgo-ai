from setuptools import setup, find_packages

setup(
    name="borgo_ai",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "typer[all]>=0.9.0",
        "rich>=13.0.0",
        "requests>=2.31.0",
        "faiss-cpu>=1.7.4",
        "numpy>=1.24.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "pypdf>=3.0.0",
        "python-docx>=0.8.11",
        "chardet>=5.0.0",
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "borgo-ai=borgo_ai.main:main",
        ],
    },
    description="Local AI CLI Assistant powered by various LLMs",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/borgo-ai",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)