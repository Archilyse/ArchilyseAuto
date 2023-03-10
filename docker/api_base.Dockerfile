FROM python:3.8.12-slim

COPY ./app/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
