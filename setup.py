from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="market-blotter",
    version="0.1.0",
    author="Justin Spahr-Summers",
    author_email="justin@jspahrsummers.com",
    description="Microservice to connect to Interactive Brokers and stream market data into Google BigQuery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/jspahrsummers/blotter",
    packages=find_packages(),
    package_data={
        "blotter": ["blotter.proto", "py.typed"],
        "blotter_client": ["py.typed"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Environment :: No Input/Output (Daemon)",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3",
        "Topic :: Internet",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    install_requires=[
        "gcloud_service @ git+https://github.com/antequant/gcloud_service@master#egg=gcloud_service",
        "google-cloud-bigquery ~= 1.22",
        "google-cloud-error-reporting ~= 0.33",
        "google-cloud-firestore ~= 1.6",
        "google-cloud-logging ~= 1.14",
        "grpcio ~= 1.25",
        "ib_insync @ git+https://github.com/erdewit/ib_insync@master#egg=ib_insync",
        "pandas ~= 0.25.3",
        "pyarrow ~= 0.15.1",
    ],
    keywords="trading investing finance ib ibkr tws",
    entry_points={
        "console_scripts": [
            "blotter = blotter.__main__:main",
            "blotter-client = blotter_client.__main__:main",
        ]
    },
)
