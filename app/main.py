from flask import Flask, request, jsonify
from collections import OrderedDict
from smart_open import open
from multiprocessing import Process
from google.cloud import storage
from time import time
import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
client = storage.Client()

app = Flask(__name__)


def upload(url, gcs_path):
    logging.info(f'Uploading to {gcs_path}')
    chunk = float(os.getenv('UPLOAD_CHUNK_IN_MB', '0.5'))
    chunk = int(chunk * 1024 * 1024)
    start = time()
    with requests.get(url, stream=True) as source:
        with open(gcs_path, 'wb', transport_params=dict(client=client)) as dest:
            for chunk in source.iter_content(chunk_size=chunk):
                dest.write(chunk)
    m, s = divmod(time() - start, 60)
    h, m = divmod(m, 60)
    logging.info(f'Upload finished {int(h)}h:{int(m)}m:{round(s, 2)}s')


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

    Process(target=upload, args=(url, gcs_path)).start()

    response['status'] = 'ok'
    response['result'] = f'Upload from {url} to {gcs_path} was started.'
    return jsonify(response)


@app.route('/', methods=['GET'])
def health_check():
    return 'Service is running', 200


if __name__ == "__main__":
    app.run(host='localhost', debug=True)
