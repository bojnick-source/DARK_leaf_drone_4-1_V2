FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /repo
COPY . /repo

RUN python -m pip install --upgrade pip \
  && python -m pip install .[dev]

CMD ["topopt", "ci-verify"]
