import base64
from datetime import datetime
import hashlib
import hmac
import json
import os
import os.path as path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib2

from flask import Flask, make_response, request, send_from_directory
from jinja2 import Environment, FileSystemLoader
from werkzeug.serving import run_simple
import requests
import scss
import yaml

from sdklib import API_ENDPOINT, logger, node_path, routeless_path, \
                   skeleton_path
from sdklib.utils import compile_stylus, compile_less, compile_coffeescript, \
                         file_data
from sdklib.wsgi import DynamicDispatcher
from sdklib.api import application


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
    wsgi = DynamicDispatcher(args.path)
    host = ''.join(args.address.split(':')[:-1])
    port = int(args.address.split(':')[-1])
    run_simple(hostname=host, port=port, application=wsgi, 
               use_reloader=True,
               use_debugger=True)


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
                # skip all files starting with ".", "#", or "_"
                if filename[0] not in '.#_':
                    filepath = path.join(dn, filename)[len(key)+1:]
                    fullfilepath = path.join(dirname, filename)
                    payload[key][filepath] = file_data(fullfilepath)

    payload['application_config'] = base64.b64encode(json.dumps(yaml_data))
    payload_json = json.dumps(payload)

    try:
        logger.info('Uploading')
        res = application.put_application(yaml_data, payload_json)
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


