FROM python:slim

RUN apt-get update
RUN apt-get install -y git

WORKDIR /usr/src/path

COPY LICENSE LICENSE
COPY README.md README.md
COPY setup.py setup.py
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir .

COPY blotter blotter

EXPOSE 50051

ENTRYPOINT [ "python", "-m", "blotter", "--port", "50051" ]