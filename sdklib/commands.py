import base64
import binascii
from datetime import datetime
import hashlib
import hmac
import json
import os
import os.path as path
import shutil
import stat
import StringIO
import sys
import urllib
import urllib2

from flask import Flask, request, url_for, send_from_directory
from jinja2 import Environment, FileSystemLoader
import requests
import yaml

from sdklib import API_ENDPOINT, logger, routeless_path, skeleton_path


def create(args):
    location = path.abspath(args.path)
    if path.exists(location):
        logger.error('Directory %s already exists' % location)
        sys.exit(1)

    logger.info('Creating project')
    if args.bootstrap:
        paths = (
            ('',),
            ('content',)
        )
    else:
        paths = (
            ('',),
            ('static',),
            ('static', 'img'),
            ('static', 'css'),
            ('static', 'js'),
            ('templates',),
            ('content',)
        )
    for p in paths:
        new_path = path.join(location, *p)
        logger.info('Creating directory %s' % new_path)
        os.mkdir(new_path)

    if args.bootstrap:
        logger.info('Copying Twitter Bootstrap framework files')
        paths_copy = ('static', 'templates')
        for p in paths_copy:
            new_path = path.join(location, p)
            bootstrap_path = path.join(skeleton_path, 'bootstrap', p)
            shutil.copytree(bootstrap_path, new_path)

    yaml_src = path.join(skeleton_path, 'app.yaml')
    yaml_dest = path.join(location, 'app.yaml')
    logger.info('Creating blank project file %s' % yaml_dest)
    shutil.copy(yaml_src, yaml_dest)
    os.chmod(yaml_dest, stat.S_IWUSR | stat.S_IRUSR)


def run_server(args):
    app_path = path.abspath(args.path)
    yaml_path = path.join(app_path, 'app.yaml')
    templates_path = path.join(app_path, 'templates')
    static_path = path.join(app_path, 'static')
    try:
        logger.info('Loading %s' % yaml_path)
        config = yaml.load(open(yaml_path, 'r').read())
    except IOError:
        logger.error('Error reading %s' % yaml_path)
        sys.exit(2)

    # if app.yaml wasn't touched, to preview something
    if config is None or 'routes' not in config:
        logger.info('No routes found in app.yaml, loading default welcome site')
        yaml_path = path.join(routeless_path, 'app.yaml')
        templates_path = path.join(routeless_path, 'templates')
        static_path = path.join(routeless_path, 'static')
        try:
            config = yaml.load(open(yaml_path, 'r').read())
        except IOError:
            logger.error('Error reading %s for default welcome site' % yaml_path)
            sys.exit(2)

    jinja_env = Environment(
        loader=FileSystemLoader(templates_path),
        extensions=['pyjade.ext.jinja.PyJadeExtension']
    )
    def _dispatch_rule(**kwargs):
        for k, v in kwargs.iteritems():
            if isinstance(v, unicode):
                kwargs[k] = str(v)
        template = jinja_env.get_template(kwargs['__sdk_template__'])
        content = _compile_defaults(kwargs['__sdk_content__'], app_path)
        for k in content:
            kwargs.setdefault(k, content[k])
        kwargs['REQ'] = request
        kwargs['GET'] = request.args
        kwargs['POST'] = request.form
        kwargs['COOKIES'] = request.cookies
        return template.render(**kwargs)

    def _dispatch_static(filename):
        return send_from_directory(static_path, filename)

    def _dispatch_favicon():
        return _dispatch_static('favicon.ico')

    def _dispatch_not_found(kwargs):
        '''
        creates the error handling function to assign to the flask object
        with flask.register_error_handler
        '''
        def not_found_handler(error):
            return _dispatch_rule(**kwargs), 404
        return not_found_handler

    def _compile_defaults(files, app_path):
        '''creates the default content dict to send to the jade template'''
        if not isinstance(files, list):
            files = [files]
        content = {}
        for f in files:
            try:
                file_path = path.join(app_path, 'content', f)
                file_type = file_path.split('.')[-1]
                file_content = {}
                with open(file_path, 'r') as fh:
                    if file_type == 'json':
                        file_content = json.load(fh)
                    elif file_type == 'yaml':
                        file_content = yaml.load(fh.read())
            except:
                logger.error('Error reading content file %s' % file_path)
            content.update(file_content)    
        return content

    app = Flask(__name__)
    i = 0
    for route in config['routes']:
        rule = route['rule']
        defaults = {}
        defaults['__sdk_template__'] = route['template']
        defaults['__sdk_content__'] = route.get('content', [])
        if rule == 404:
            # 404
            app.register_error_handler(404, _dispatch_not_found(defaults))
        else:
            # adding rules with actual uri patterns
            endpoint = 'dispatch_%s' % str(i)
            app.add_url_rule(
                rule,
                endpoint,
                _dispatch_rule,
                defaults=defaults
            )
            i += 1
    app.add_url_rule('/static/<path:filename>', 'static', _dispatch_static)
    app.add_url_rule('/favicon.ico', 'favicon', _dispatch_favicon)

    host = ''.join(args.address.split(':')[:-1])
    port = int(args.address.split(':')[-1])
    app.run(host=host, port=port, debug=True)


def upload(args):
    app_path = path.abspath(args.path)
    yaml_path = path.join(app_path, 'app.yaml')
    templates_path = path.join(app_path, 'templates')
    content_path = path.join(app_path, 'content')
    static_path = path.join(app_path, 'static')
    
    yaml_data = yaml.load(open(yaml_path, 'r').read())
    if 'api_access_key' not in yaml_data or \
       'api_secret_key' not in yaml_data:
        logger.error('app.yaml does not have data for keys "api_access_key" and "api_secret_key"')
        sys.exit(3)
        
    payload = {}
    cut_start = len(app_path) + 1
    for dirname, subdirs, files in os.walk(app_path):
        dn = dirname[cut_start:]
        if dn.startswith('templates') or \
           dn.startswith('content') or \
           dn.startswith('static'):
            if dn.startswith('templates'):
                key = 'templates'
            if dn.startswith('content'):
                key = 'content'
            if dn.startswith('static'):
                key = 'static'
            payload.setdefault(key, {})
            for filename in files:
                filepath = path.join(dn, filename)[len(key)+1:]
                fullfilepath = path.join(dirname, filename)
                payload[key][filepath] = _file_data(fullfilepath)

    payload['application_config'] = base64.b64encode(json.dumps(yaml_data))
    payload_json = json.dumps(payload)

    try:
        logger.info('Uploading')
        res = _upload_file(yaml_data, payload_json)
        logger.debug(
            'Response code: %s\n'
            'Response headers: %s\n'
            'Response body: %s' % (res.status_code, res.headers, res.content)
        )

        try:
            response_data = json.loads(res.content)
        except:
            response_data = {'success': True}

        if response_data['success']:
            logger.info(
                'Upload complete. Your site is available at '
                'http://%s.app.markuphive.com/' % yaml_data['application_name']
            )
        else:
            logger.info('Upload failed.')
            if 'error-message' in response_data:
                logger.info(
                    'Error message: %s' % response_data['error-message']
                )
    except urllib2.HTTPError, e:
        logger.error('API call returned a 404. Please check api '
                     'credentials in the app.yaml file.')


def _file_data(filename):
    with open(filename, 'r') as fh:
        data = fh.read()
        data64 = base64.b64encode(data)
        return data64

def _api_signature(verb, content, date, uri, secret):
    content_hash = ''
    if content != '':
        content_hash = _hash(content).hexdigest()
    msg = '\n'.join([verb, content_hash, date, uri])
    signer = hmac.new(secret, msg, hashlib.sha1)
    signature = signer.digest()
    signature64 = base64.b64encode(signature)
    return signature64

def _date_header():
    '''
    returns date string formatted to RFC1123 specified here in the first
    format shown.
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1
    '''
    dt = datetime.utcnow()
    header = dt.strftime('%a, %d %b %y %H:%M:%S GMT')
    return header

def _upload_file(app_data, payload):
    name = app_data['application_name']
    endpoint = '%s/api/application/%s/' % (API_ENDPOINT, name)
    endpoint = endpoint % app_data['application_name']
    access_key = app_data['api_access_key']
    secret_key = app_data['api_secret_key']
    api_verb = 'PUT'
    api_content = payload
    api_date = _date_header()
    api_uri = '/api/application/%s/' % name
    api_signature = _api_signature(
        api_verb, api_content, api_date, api_uri, secret_key
    )
    headers = {
        'Date': api_date,
        'X-Authentication': '%s:%s' % (access_key, api_signature)
    }
    res = requests.put(endpoint, data=payload, headers=headers, verify=True)
    return res

def _hash(content):
    h = hashlib.sha1()
    h.update(content)
    return h
