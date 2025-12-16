"""
Setup script for development installation.
"""

from setuptools import setup, find_packages

setup(
    name="omnisearch-pro",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "customtkinter>=5.2.0",
    ],
    python_requires=">=3.11",
    author="WeUP Team / memarzade.dev",
    description="Enterprise-grade local file search engine",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/memarzade-dev/omnisearch-pro",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: System :: Filesystems",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)