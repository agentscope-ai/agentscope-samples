# -*- coding: utf-8 -*-
"""Setup script for AgentScope."""
import re
import setuptools

VERSION = "0.1.0"

NAME = "agentscope-samples"
URL = "https://github.com/agentscope-ai/agentscope-samples"
minimal_requires = []
extra_requires = [
    "agentscope[dev]>=1.0.5",
    "agentscope_runtime>=0.1.5",
    "pyyaml>=6.0.2",
    "quart>=0.8.0",
    "quart-cors>=0.8.0",
    "flask_sqlalchemy>=3.1.1",
    "flask>=3.1.2",
    "flask_cors>=6.0.1",
]
dev_requires = [
    "pre-commit",
    "pytest",
    "sphinx-gallery",
    "furo",
    "myst_parser",
    "matplotlib",
]
with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()
setuptools.setup(
    name=NAME,
    version=VERSION,
    author="SysML team of Alibaba Tongyi Lab ",
    description="AgentScope Sample Agents: Ready-to-use multi-agent examples built on AgentScope and AgentScope Runtime.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=URL,
    download_url=f"{URL}/archive/v{VERSION}.tar.gz",
    keywords=["deep-learning", "multi agents", "agents"],
    packages=[],
    install_requires=minimal_requires,
    extras_require={
        "full": minimal_requires + extra_requires,
        "dev": minimal_requires + extra_requires + dev_requires,
    },
    license="Apache-2.0",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    entry_points={},
)
