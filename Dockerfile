FROM python:3.8-alpine3.12

RUN apk --no-cache add \
    curl \
    bash \
    libffi-dev \
    gcc \
    musl-dev

RUN pip install --upgrade pip
RUN pip install gunicorn

# Copy python requirements file
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

RUN curl https://sdk.cloud.google.com | bash
ENV PATH $PATH:/root/google-cloud-sdk/bin

# Remove pip cache. We are not going to need it anymore
RUN rm -r /root/.cache

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY ./app ./

CMD exec ./start.sh