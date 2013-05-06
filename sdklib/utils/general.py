import base64
import hashlib
import json
import os.path
import subprocess
import sys
import tempfile
from types import IntType, StringType

from werkzeug import Request

from sdklib import node_path



def file_data(filename):
    '''
    Get file data in base64 for upload
    '''
    with open(filename, 'r') as fh:
        data = fh.read()
        data64 = base64.b64encode(data)
        return data64


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


def api_parse(default):
    '''
    Decorator to take web response data (at this point it should already be 
    parsed as a JSON string) and remove the 'success' and 'result' keys, 
    returning the default parameter if 'success' if False
    '''
    def json_result(*args, **kwargs):
        result = fn(*args, **kwargs)
        return json.loads(result.content)
    return json_result


class PathUtil(object):
    '''
    Used to get path names for use in templates.

    Usage:
    
    path = PathUtil(wsgi.environ)
    path() full path
    path(n) n segment, 0 based index
    '''

    def __init__(self, environ):
        path = environ.get('PATH_INFO')
        self.path = path
        self.paths = path.strip('/').split('/')
        self.placeholders = {}

    def __call__(self, index=None):
        if index is None:
            return self.path
        elif type(index) is IntType and len(self.paths) > index:
            return self.paths[index]
        elif type(index) is StringType:
            return self.placeholders.get(index, '')
        return ''

    def add_placeholders(self, placeholders):
        self.placeholders = {
            k: v for k, v in placeholders.items() if not k.startswith('_')
        }


class GetUtil(object):
    '''
    Used to query for GET variables
    '''

    def __init__(self, environ):
        req = Request(environ)
        self.args = req.args

    def __call__(self, name):
        return self.args.get(name, '')

    def list(self, name):
        return self.args.getlist(name)
        
