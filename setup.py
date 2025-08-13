"""Minimal setup.py for development installation."""
from setuptools import setup, find_packages

setup(
    name="ami-web",
    version="0.1.0",
    packages=find_packages(include=["backend", "backend.*"]),
    python_requires=">=3.12",
    install_requires=[
        # Core dependencies are listed in requirements.txt
        # This is just for editable install support
    ],
    author="AMI",
)