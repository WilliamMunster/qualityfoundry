from setuptools import setup, find_packages

setup(
    name="qualityfoundry",
    version="0.1.0",
    package_dir={"": "app"},
    packages=find_packages("app"),
)
