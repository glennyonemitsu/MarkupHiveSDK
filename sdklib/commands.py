import base64
from datetime import datetime
import hashlib
import hmac
import json
import os
import os.path as path
import platform
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib2

from flask import Flask, make_response, request, send_from_directory
from jinja2 import Environment, FileSystemLoader
import requests
import scss
import yaml

from sdklib import API_ENDPOINT, logger, node_path, routeless_path, \
                   skeleton_path
from sdklib.utils.general import compile_stylus, compile_less, \
                                 compile_coffeescript, file_data
from sdklib.wsgi import DynamicDispatcher, LocalServer, SourceWatcher
from sdklib.api import MarkupHive


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
    statics = {}

    server = LocalServer(args, statics)
    watcher = SourceWatcher(args, statics)

    server_thread = threading.Thread(target=server, name='Local Server')
    watcher_thread = threading.Thread(target=watcher, name='Source Watcher')
    server_thread.daemon = True
    watcher_thread.daemon = True

    def signal_handler(signum, frame):
        logger.info('Got signal. Shutting down local server.')
        sys.exit(0)

    signal.signal(signal.SIGABRT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server_thread.start()
    watcher_thread.start()

    while True:
        time.sleep(10)


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

    api = MarkupHive(yaml_data)

    try:
        logger.info('Uploading')
        response_data = api.put_application(payload_json)
        logger.debug('API response data: {response}'.format(response=response_data))

        if response_data['success']:
            logger.info(
                'Upload complete. Your site is available at '
                'http://%s.app.markuphive.com/' % yaml_data['application_name']
            )
        else:
            logger.info('Upload failed.')
            if 'error' in response_data:
                for error in response_data['error']:
                    logger.info('Error message: {error}'.format(error=error))
    except urllib2.HTTPError, e:
        logger.error('API call returned a 404. Please check api '
                     'credentials in the app.yaml file.')


