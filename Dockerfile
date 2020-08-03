FROM python:3.8-slim

RUN pip install --upgrade pip
RUN pip install gunicorn

# Copy python requirements file
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Remove pip cache. We are not going to need it anymore
RUN rm -r /root/.cache

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY ./app ./

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app