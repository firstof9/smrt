"""Setup module for tplink-ess-lib."""
from pathlib import Path

from setuptools import find_packages, setup

PROJECT_DIR = Path(__file__).parent.resolve()
README_FILE = PROJECT_DIR / "README.md"
VERSION = "0.3.1"

setup(
    name="tplink-ess-lib",
    version=VERSION,
    url="https://github.com/firstof9/tplink-ess-lib",
    download_url="https://github.com/firstof9/tplink-ess-lib",
    author="firstof9",
    author_email="firstof9@gmail.com",
    description="Python package and software for the TP-Link TL-SG105E and TL-SG108E smart switches",
    long_description=README_FILE.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["test.*", "tests"]),
    python_requires=">=3.8",
    install_requires=["netifaces"],
    entry_points={},
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)