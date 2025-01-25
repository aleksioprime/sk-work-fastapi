FROM python:3.11.9-slim

RUN apt-get update && apt-get install -y postgresql-client && apt-get clean

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

RUN pip install --upgrade pip

COPY ./requirements.txt ./

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD sh entrypoint.sh