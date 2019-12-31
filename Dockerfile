FROM python:3.7-slim

RUN apt-get update
RUN apt-get install -y git

WORKDIR /usr/src/path

COPY LICENSE LICENSE
COPY README.md README.md
COPY setup.py setup.py
COPY wheels wheels
RUN pip install --only-binary pyarrow --no-cache-dir --find-links=wheels .

COPY blotter blotter

EXPOSE 50051

ENTRYPOINT [ "python", "-m", "blotter", "--port", "50051" ]