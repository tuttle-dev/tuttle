#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("requirements.txt") as requirements_file:
    requirements = requirements_file.readlines()

with open("requirements_dev.txt") as dev_requirements_file:
    dev_requirements = dev_requirements_file.readlines()

setup(
    author="Christian Staudt",
    author_email="mail@clstaudt.me",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    description="Painless business planning for freelancers.",
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + "\n\n",
    include_package_data=True,
    keywords="tuttle",
    name="tuttle",
    packages=find_packages(include=["tuttle", "tuttle.*"]),
    test_suite="tests",
    url="https://github.com/tuttle-dev/tuttle",
    version="0.0.9",
    zip_safe=False,
)
