'''
WSGI dispatcher for run_server subcommand

This is the front facing WSGI app that dynamically creates a new flask app
with dispatchers for every request. This ensures all files including the
app.yaml file is loaded and recompiled.
'''
import glob
import json
import os
import os.path
import sys
import threading
import time

from flask import Flask, abort, make_response, request, send_from_directory
from jinja2 import Environment, FileSystemLoader
import scss
import werkzeug
from werkzeug.serving import run_simple
import yaml

from sdklib import logger, routeless_path
from sdklib.api import MarkupHive
from sdklib.utils.cms import CMSUtil
from sdklib.utils.general import compile_stylus, compile_less, \
                                 compile_coffeescript, PathUtil, \
                                 GetUtil, StaticUtil, markdown


class DynamicDispatcher(object):

    def __init__(self, app_path, statics):
        self.app_path = os.path.abspath(app_path)
        self.statics = statics

    def set_app_path(self, app_path):
        '''sets the root path to serve templates and files from'''
        self.app_yaml_path = os.path.join(app_path, 'app.yaml')
        self.templates_path = os.path.join(app_path, 'templates')
        self.static_path = os.path.join(app_path, 'static')
        self.content_path = os.path.join(app_path, 'content')
        
    def load_app_yaml(self, path=None):
        # default to the initialized path set with command args
        if path is None:
            self.set_app_path(self.app_path)
        else:
            self.set_app_path(path)

        try:
            with open(self.app_yaml_path, 'r') as yaml_file:
                self.app_yaml = yaml.safe_load(yaml_file.read())
        except IOError:
            logger.error('Cannot load %s' % self.app_yaml_path)
            sys.exit(2)
        except yaml.YAMLError as e:
            logger.error('Cannot parse yaml file %s' % self.app_yaml_path)
            sys.exit(2)

    def setup_jinja(self):
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_path),
            extensions=['pyjade.ext.jinja.PyJadeExtension']
        )
        
    def __call__(self, environ, start_response):
        try:
            self.load_app_yaml()

            # if app.yaml has no routes use default welcome site
            if self.app_yaml is None or 'routes' not in self.app_yaml:
                self.load_app_yaml(routeless_path)

            if self.app_yaml is None or \
              'application_name' not in self.app_yaml or \
              'api_access_key' not in self.app_yaml or \
              'api_secret_key' not in self.app_yaml:
                api = None
            else:
                api = MarkupHive(self.app_yaml)
            cms = CMSUtil(api)

            self.setup_jinja()

            get = GetUtil(environ)
            path = PathUtil(environ)
            static = StaticUtil()

            app = Flask(__name__)
            i = 0
            for route in self.app_yaml['routes']:
                rule = route['rule']
                # hidden data we tack on to use when serving
                defaults = {
                    '__sdk_template__': route['template'],
                    '__sdk_content__': route.get('content', []),
                    '__utils__': {
                        'deployment': 'sdk',
                        'cms': cms,
                        'get': get,
                        'path': path,
                        'static': static,
                        'markdown': markdown,
                    }
                }

                # register special 404 rule
                if rule == 404:
                    app.register_error_handler(404, self._dispatch_not_found(defaults))

                # register regular rules with actual URI patterns
                else:
                    endpoint = 'dispatch_{index}'.format(index=i)
                    app.add_url_rule(rule,
                                     endpoint, 
                                     self._dispatch_rule,
                                     defaults=defaults)
                    i += 1
            app.add_url_rule('/static/<path:filename>', 
                             'static', 
                             self._dispatch_static)
            app.add_url_rule('/favicon.ico', 
                             'favicon', 
                             self._dispatch_favicon)
            app.add_url_rule('/robots.txt', 
                             'robotstxt', 
                             self._dispatch_robots)
            return app.wsgi_app(environ, start_response)
        except Exception as e:
            logger.error('WSGI request dispatch exception: {e}'.format(e=e))

    def _dispatch_rule(self, *args, **kwargs):
        # potentially these might be used in the templates. These are not 
        # supplied in production so we will remove them and any others.
        template_name = kwargs.pop('__sdk_template__')
        content_files = kwargs.pop('__sdk_content__')
        
        # markdown never goes through jinja, so check and compile it straight
        # markdown also doesn't use template variables, so compile_defaults() 
        # is skipped
        if template_name.endswith('.md'):
            template_name = os.path.join(self.templates_path, template_name)
            with open(template_name, 'r') as th:
                return markdown(th.read())

        # everything else goes through jinja2
        else:
            template = self.jinja_env.get_template(template_name)
            content = self._compile_defaults(content_files)

            utils = kwargs.pop('__utils__')
            deployment = utils.get('deployment')
            cms = utils.get('cms')
            get = utils.get('get')
            path = utils.get('path')
            path.add_placeholders(kwargs)
            static = utils.get('static')
            markdown = utils.get('markdown')

            context = { 'cms': cms,
                        'content': content,
                        'deployment': deployment,
                        'get': get,
                        'path': path,
                        'markdown': markdown,
                        'static': static}
            return template.render(**context)

    def _dispatch_static(self, filename):
        static_file = os.path.join(self.static_path, filename)

        # special compiled files will be pre-compiled by the SourceWatcher
        if filename.startswith('js/') or filename.startswith('css/'):

            if static_file not in self.statics:
                return abort(404)
            else:
                res = make_response()
                res.data = self.statics[static_file]['data']
                if filename.startswith('css/'):
                    res.mimetype = 'text/css'
                elif filename.startswith('js/'):
                    res.mimetype = 'application/javascript'
                return res

        elif not os.path.isfile(static_file):
            return abort(404)

        else:
            return send_from_directory(static_file)

    def _dispatch_favicon(self):
        return self._dispatch_static('favicon.ico')

    def _dispatch_robots(self):
        '''How awesome would this be?'''
        return self._dispatch_static('robots.txt')

    def _dispatch_not_found(self, kwargs):
        '''
        creates the error handling function to assign to the flask object
        with flask.register_error_handler
        '''
        def not_found_handler(error):
            return self._dispatch_rule(**kwargs), 404
        return not_found_handler

    def _compile_defaults(self, files):
        '''creates the default content dict to send to the jade template'''
        if not isinstance(files, list):
            files = [files]

        content = {}
        for f in files:
            try:
                file_path = os.path.join(self.content_path, f)
                with open(file_path, 'r') as fh:
                    if file_path.endswith('.json'):
                        file_content = json.load(fh)
                    elif file_path.endswith('.yaml'):
                        file_content = yaml.safe_load(fh.read())
                    else:
                        logger.info('Skipping content file due to unrecognized file format %s' % file_path)
                        file_content = {}
            except:
                logger.error('Error reading content file %s' % file_path)
            content.update(file_content)    
        return content


class LocalServer(object):

    def __init__(self, args, statics):
        self.wsgi = DynamicDispatcher(args.path, statics)
        self.args = args
        self.statics = statics

    def __call__(self):
        logger.info('Running local server')
        host = ''.join(self.args.address.split(':')[:-1])
        port = int(self.args.address.split(':')[-1])
        run_simple(hostname=host, 
                   port=port, 
                   application=self.wsgi, 
                   use_debugger=True)


class SourceWatcher(object):

    def __init__(self, args, statics):
        self.args = args
        self.path = args.path
        self.statics = statics

    def __call__(self):
        
        logger.info('Running source code watcher')
        while True:
            app_path = os.path.abspath(self.path)
            
            css_path = os.path.join(app_path, 'static', 'css')
            js_path = os.path.join(app_path, 'static', 'js')

            static_files = [f for f in glob.glob(css_path + '/*') if os.path.isfile(f)]
            static_files += [f for f in glob.glob(css_path + '/**/*') if os.path.isfile(f)]
            static_files += [f for f in glob.glob(js_path + '/*') if os.path.isfile(f)]
            static_files += [f for f in glob.glob(js_path + '/**/*') if os.path.isfile(f)]

            for f in static_files:
                try:
                    mtime = os.path.getmtime(f)
                    if f not in self.statics or mtime > self.statics[f]['mtime']:
                        if f in self.statics and mtime > self.statics[f]['mtime']:
                            logger.debug('Found new file update for: {0}'.format(f))
                        if f.startswith(css_path):
                            data = self.process_css(f)
                        elif f.startswith(js_path):
                            data = self.process_js(f)
                        self.statics[f] = {'mtime': mtime, 'data': data}
                except OSError as e:
                    # ignoring OS Errors since it could be an editor creating 
                    # scratch files momentarily
                    pass

            time.sleep(1.0)

    def process_css(self, filename):

        # regular css
        if filename.endswith('.css'):
            css = open(filename).read()

        # scss support
        if filename.endswith('.scss'):
            _scss = scss.Scss()
            css = _scss.compile(scss_file=filename)

        # stylus support
        elif filename.endswith('.styl'):
            css = compile_stylus(filename)

        # less support
        elif filename.endswith('.less'):
            css = compile_less(filename)

        return css

    def process_js(self, filename):

        # regular javascript
        if filename.endswith('.js'):
            js = open(filename).read()

        # coffeescript support
        elif filename.endswith('.coffee'):
            js = compile_coffeescript(filename)

        return js
