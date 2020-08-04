from flask import Flask, request, jsonify
from collections import OrderedDict
from smart_open import open
from google.cloud import storage
from time import time
import os
import requests
import logging
import datetime

try:
    import settings
except ImportError:
    from . import settings

logging.basicConfig(level=logging.INFO)
client = storage.Client()

app = Flask(__name__)


def time_check(start, finish):
    m, s = divmod(finish - start, 60)
    h, m = divmod(m, 60)
    return f'{int(h)}h:{int(m)}m:{round(s, 2)}s'


def upload(url, gcs_path):
    logging.info(f'Uploading to {gcs_path}')
    chunk = float(os.getenv('UPLOAD_CHUNK_IN_MB', '0.5'))
    chunk = int(chunk * 1024 * 1024)
    start = time()
    with requests.get(url, stream=True) as source:
        with open(gcs_path, 'wb', transport_params=dict(client=client)) as dest:
            logging.info(f'Read and write were ready in {time_check(start, time())}')
            chunk_read_time = time()
            for chunk in source.iter_content(chunk_size=chunk):
                logging.info(f'chunk read time {time_check(chunk_read_time, time())}')
                chunk_write = time()
                dest.write(chunk)
                logging.info(f'chunk write time {time_check(chunk_write, time())}')
                chunk_read_time = time()

    logging.info(f'Upload finished in {time_check(start, time())}')


def bucket():
    return client.bucket(settings.bucket_name)


def file_exists(filename):
    return bucket().blob(filename).exists()


@app.route('/api/upload/', methods=['POST'])
def start_upload():
    content = request.json
    response = OrderedDict()

    url = content.get('url', '')
    if not url:
        response['status'] = 'failed'
        response['error'] = 'Valid url field is required.'
        return jsonify(response), 400

    filename = content.get('filename', '')
    if not filename:
        response['status'] = 'failed'
        response['error'] = 'Valid filename is required.'
        return jsonify(response), 400

    if file_exists(filename):
        response['status'] = 'failed'
        response['error'] = f'{filename} already exists.'
        return jsonify(response), 400

    try:
        source = requests.get(url, stream=True)
        source.raise_for_status()
    except requests.RequestException as err:
        response['status'] = 'failed'
        response['error'] = f'Failed to open {url}.'
        logging.info(err)
        return jsonify(response), 400
    else:
        source.close()

    gcs_path = f'gs://{settings.bucket_name}/{filename}'
    upload(url, gcs_path)

    response['status'] = 'ok'
    response['result'] = f'{url} was uploaded to {filename}.'
    return jsonify(response), 201


@app.route('/', methods=['GET'])
def health_check():
    if not settings.bucket_name:
        return 'BUCKET environment variable is not defined.', 500

    return f'URL to GCS service version {settings.version}', 200


@app.route('/api/upload-url/', methods=['POST'])
def signed_upload_url():
    content = request.json
    filename = content.get('filename', '')
    response = OrderedDict()
    if not filename:
        response['status'] = 'failed'
        response['error'] = 'Valid filename is required.'
        return jsonify(response), 400

    prefixed_filename = settings.signed_prefix + filename.strip('/')
    if file_exists(prefixed_filename):
        response['status'] = 'failed'
        response['error'] = f'{filename} already exists.'
        return jsonify(response), 400

    blob = bucket().blob(prefixed_filename)
    url = blob.generate_signed_url(
        expiration=datetime.timedelta(minutes=60),
        method='POST', version="v4")

    response['status'] = 'ok'
    response['result'] = url
    return jsonify(response), 201


if __name__ == "__main__":
    app.run(host='localhost', debug=True)
