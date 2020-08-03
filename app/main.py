from flask import Flask, request, jsonify
from collections import OrderedDict
from smart_open import open
from google.cloud import storage
from time import time
import os
import requests
import logging

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


def file_exists(bucket_name, filename):
    return client.bucket(bucket_name).blob(filename).exists()


@app.route('/api/upload/', methods=['POST'])
def start_upload():
    bucket_name = os.environ['BUCKET']
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

    if file_exists(bucket_name, filename):
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

    gcs_path = f'gs://{bucket_name}/{filename}'
    upload(url, gcs_path)

    response['status'] = 'ok'
    response['result'] = f'{url} was uploaded to {filename}.'
    return jsonify(response)


@app.route('/', methods=['GET'])
def health_check():
    return f'URL to GCS service version {settings.version}', 200


if __name__ == "__main__":
    app.run(host='localhost', debug=True)
