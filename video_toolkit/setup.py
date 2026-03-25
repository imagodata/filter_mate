"""
Setup script for Video Toolkit.

Install as editable package:
    pip install -e .

Install from source:
    pip install .
"""

from setuptools import setup, find_packages
from pathlib import Path

here = Path(__file__).parent
readme = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="video-toolkit",
    version="1.0.0",
    description="Reusable toolkit for automated desktop application tutorial video production",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Video Toolkit Contributors",
    python_requires=">=3.10",
    packages=find_packages(include=["toolkit", "toolkit.*"]),
    package_data={
        "toolkit": [],
    },
    install_requires=[
        "pyautogui>=0.9.54",
        "obsws-python>=1.7.2",
        "edge-tts>=6.1.9",
        "mutagen>=1.47.0",
        "click>=8.1.7",
        "pyyaml>=6.0.1",
        "pyperclip>=1.9.0",
    ],
    extras_require={
        "diagrams": ["playwright>=1.42.0"],
        "windows": ["pywin32>=308"],
        "elevenlabs": ["elevenlabs>=1.0.0"],
        "all": ["playwright>=1.42.0", "pywin32>=308"],
    },
    entry_points={
        "console_scripts": [
            # No top-level entry point — projects provide their own run.py
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "video automation", "screen recording", "tutorial video",
        "pyautogui", "obs", "tts", "mermaid", "ffmpeg",
    ],
)
