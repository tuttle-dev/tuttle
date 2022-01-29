#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "pandas",
    "pandera",
    "altair",
    "sqlmodel",
    "pyicloud",
    "loguru",
    "pydantic[email]",
    "pydentic",
    "fints",
    "ics",
    "babel",
]

dev_requirements = [
    "jupyterlab",
    "ipywidgets",
]

test_requirements = [
    "pytest>=3",
]


setup(
    author="Christian Staudt",
    author_email="mail (at) clstaudt.me",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    description="Painless business planning for freelancers.",
    install_requires=requirements + test_requirements,
    license="GNU General Public License v3",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="tuttle",
    name="tuttle",
    packages=find_packages(include=["tuttle", "tuttle.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/tuttle-dev/tuttle",
    version="0.0.2",
    zip_safe=False,
)
