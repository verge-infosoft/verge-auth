from setuptools import setup, find_packages

setup(
    name="verge-auth",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "httpx"
    ],
)
