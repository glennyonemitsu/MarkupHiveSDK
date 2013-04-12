import base64
from datetime import datetime
import hashlib
import hmac
import os.path
import subprocess
import sys
import tempfile

import requests

from sdklib import API_ENDPOINT, node_path



def file_data(filename):
    '''
    Get file data in base64 for upload
    '''
    with open(filename, 'r') as fh:
        data = fh.read()
        data64 = base64.b64encode(data)
        return data64


def api_signature(verb, content, date, uri, secret):
    content_hash = ''
    if content != '':
        content_hash = hash(content).hexdigest()
    msg = '\n'.join([verb, content_hash, date, uri])
    signer = hmac.new(secret, msg, hashlib.sha1)
    signature = signer.digest()
    signature64 = base64.b64encode(signature)
    return signature64


def date_header():
    '''
    returns date string formatted to RFC1123 specified here in the first
    format shown.
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1
    '''
    dt = datetime.utcnow()
    header = dt.strftime('%a, %d %b %y %H:%M:%S GMT')
    return header


def upload_file(app_data, payload):
    name = app_data['application_name']
    endpoint = '%s/v0/application/%s/' % (API_ENDPOINT, name)
    access_key = app_data['api_access_key']
    secret_key = app_data['api_secret_key']
    api_verb = 'PUT'
    api_content = payload
    api_date = date_header()
    api_uri = '/v0/application/%s/' % name
    signature = api_signature(
        api_verb, api_content, api_date, api_uri, secret_key
    )
    headers = {
        'Date': api_date,
        'X-Authentication': '%s:%s' % (access_key, signature)
    }
    res = requests.put(endpoint, data=payload, headers=headers)
    return res


def hash(content):
    h = hashlib.sha1()
    h.update(content)
    return h


def compile_coffeescript(filename):
    return node_command(['coffee-script', 'bin', 'coffee'], ['--print', filename])


def compile_less(filename):
    return node_command(['less', 'bin', 'lessc'], [filename])


def compile_stylus(filename):
    return node_command(['stylus', 'bin', 'stylus'], stdin=filename)


def node_command(command, args=[], stdin=None):
    '''
    convenience method to call node and additional node commands installed
    from npm such as coffeescript or less.

    command is the relative path list to the command
    args are the additional parameters to pass after the command
    '''
    # these are 64bit binaries
    if sys.platform.startswith('linux'):
        node_name = 'node-linux'
    elif sys.platform.startswith('darwin'):
        node_name = 'node-darwin'
    node = os.path.join(node_path, node_name)
    command = os.path.join(node_path, *command)
    output = tempfile.TemporaryFile()
    cmd_args = [node, command] + args
    if stdin is None:
        subprocess.call(cmd_args, stdout=output)
    else:
        stdinfh = open(stdin, 'r')
        subprocess.call(cmd_args, stdin=stdinfh, stdout=output)
        stdinfh.close()
    output.seek(0)
    return output.read()


