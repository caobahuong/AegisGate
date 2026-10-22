from setuptools import find_packages, setup

setup(
    name="aegisgate-sdk",
    version="1.0.0",
    description="Official SDK for developing database connectors and plugins for AegisGate Zero-Trust Gateway",
    author="AegisGate Team",
    packages=find_packages(),
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

