'''
Base helper functions for all API Related operations
'''
import base64
from datetime import datetime
import hashlib
import hmac

import requests

from sdklib import API_ENDPOINT
from sdklib.utils import hash


def signature(verb, content, date, uri, secret):
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


def call(verb, uri, payload, app_config, api_endpoint=None):
    '''
    callable for all api calls

    this handles all signature creation and date header preparation
    '''
    access_key = app_config['api_access_key']
    secret_key = app_config['api_secret_key']

    domain = api_endpoint if api_endpoint is not None else API_ENDPOINT
    endpoint = '{domain}{endpoint}'.format(domain=domain, endpoint=uri)

    date = date_header()
    sign = signature(verb, payload, date, uri, secret_key)
    auth_header = '{key}:{sign}'.format(key=access_key, sign=sign)
    headers = {'Date': date, 'X-Authentication': auth_header}

    requester = getattr(requests, verb.lower())
    res = requester(endpoint, data=payload, headers=headers)
    return res


