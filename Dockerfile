FROM python:slim

WORKDIR /usr/src/path

COPY blotter blotter
COPY setup.py setup.py
COPY LICENSE LICENSE
COPY README.md README.md
RUN pip install --no-cache-dir .

EXPOSE 50051
ENTRYPOINT [ "blotter", "--port", "50051" ]