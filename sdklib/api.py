'''
Base helper functions for all API Related operations
'''
import base64
from datetime import datetime
import hashlib
import hmac

import requests

from sdklib import API_ENDPOINT
from sdklib.utils.general import hash


def date_header():
    '''
    returns date string formatted to RFC1123 specified here in the first
    format shown.
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1
    '''
    dt = datetime.utcnow()
    header = dt.strftime('%a, %d %b %y %H:%M:%S GMT')
    return header


def uri(api_uri):
    '''
    API class method wrapper to specify the API uri to use.

    The API class object holds state, specifically MarkupHive.api_uri that the
    method MarkupHive.(get|post|put|etc.) refers to upon call.
    '''
    def decorator(fn):
        def wrapped_func(self, *args, **kwargs):
            self.api_uri = api_uri
            return fn(self, *args, **kwargs)
        return wrapped_func
    return decorator



class MarkupHive(object):

    def __init__(self, app_config, api_endpoint=None):
        self.app_name = app_config['application_name']
        self.access_key = app_config['api_access_key']
        self.secret_key = app_config['api_secret_key']
        self.domain = api_endpoint if api_endpoint is not None else API_ENDPOINT

    def call(self, verb, payload, uri_vars={}, get_vars={}):
        '''
        callable for all api calls

        this handles all signature creation and date header preparation
        '''

        uri = self.api_uri.format(**uri_vars)
        endpoint = '{domain}{endpoint}'.format(domain=self.domain, endpoint=uri)


        date = date_header()
        sign = self.signature(verb, payload, date, uri)
        auth_header = '{key}:{sign}'.format(key=self.access_key, sign=sign)
        headers = {'Date': date, 'X-Authentication': auth_header}

        requester = getattr(requests, verb.lower())
        res = requester(endpoint, params=get_vars, data=payload, headers=headers)
        return res

    def signature(self, verb, content, date, uri):
        content_hash = ''
        if content != '':
            content_hash = hash(content).hexdigest()
        msg = '\n'.join([verb, content_hash, date, uri])
        signer = hmac.new(self.secret_key, msg, hashlib.sha1)
        signature = signer.digest()
        signature64 = base64.b64encode(signature)
        return signature64

    def get(self, uri_vars={}, get_vars={}):
        return self.call('GET', '', uri_vars, get_vars)

    def put(self, payload, uri_vars={}, get_vars={}):
        return self.call('PUT', payload, uri_vars, get_vars)

    @uri('/v1/cms/content-types/')
    def get_cms_content_types(self):
        return self.get()

    @uri('/v0/application/{name}/')
    def put_application(self, payload):
        return self.put(payload, dict(name=self.app_name))


