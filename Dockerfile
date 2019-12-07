# Builder
FROM python:slim AS builder

WORKDIR /usr/src/path

RUN python -m pip install --upgrade --no-cache-dir pip
RUN pip install --upgrade --no-cache-dir wheel

COPY blotter blotter
COPY setup.py setup.py
COPY LICENSE LICENSE
COPY README.md README.md

RUN python setup.py bdist_wheel

# Application
FROM python:slim

WORKDIR /usr/src/path

COPY --from=builder /usr/src/path/dist dist
RUN pip install --no-cache-dir dist/*.whl

EXPOSE 50051
ENTRYPOINT [ "blotter", "--port", "50051" ]