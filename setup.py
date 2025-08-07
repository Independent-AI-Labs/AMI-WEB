from pathlib import Path

from setuptools import find_packages, setup

readme_path = Path("README.md")
with readme_path.open(encoding="utf-8") as fh:
    long_description = fh.read()

requirements_path = Path("requirements.txt")
with requirements_path.open(encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="chrome-manager",
    version="0.1.0",
    author="Chrome Manager Team",
    description="Enterprise headless Chrome instance manager with MCP support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/chrome-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "chrome-manager=chrome_manager.cli:main",
            "chrome-mcp-server=chrome_manager.mcp_server:main",
        ],
    },
)
