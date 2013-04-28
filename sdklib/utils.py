import base64
import hashlib
import os.path
import subprocess
import sys
import tempfile

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


