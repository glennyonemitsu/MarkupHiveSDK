'''
WSGI dispatcher for run_server subcommand

This is the front facing WSGI app that dynamically creates a new flask app
with dispatchers for every request. This ensures all files including the
app.yaml file is loaded and recompiled.
'''
import json
import os.path
import sys

from flask import Flask, abort, make_response, request, send_from_directory
from jinja2 import Environment, FileSystemLoader
from markdown import markdown
import scss
import werkzeug
import yaml

from sdklib import API_ENDPOINT, logger, node_path, routeless_path, \
                   skeleton_path
from sdklib.utils import compile_stylus, compile_less, compile_coffeescript, \
                         file_data, upload_file


class DynamicDispatcher(object):

    def __init__(self, app_path):
        self.app_path = os.path.abspath(app_path)

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
        self.load_app_yaml()

        # if app.yaml has no routes use default welcome site
        if self.app_yaml is None or 'routes' not in self.app_yaml:
            self.load_app_yaml(routeless_path)

        self.setup_jinja()

        app = Flask(__name__)
        i = 0
        for route in self.app_yaml['routes']:
            rule = route['rule']
            # hidden data we tack on to use when serving
            defaults = {'__sdk_template__': route['template'],
                        '__sdk_content__': route.get('content', []),
                        '_deployment_': 'sdk'}

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
        return app.wsgi_app(environ, start_response)

    def _dispatch_rule(self, **kwargs):
        for k, v in kwargs.iteritems():
            if isinstance(v, unicode):
                kwargs[k] = str(v)

        template_name = kwargs['__sdk_template__']
        content_files = kwargs['__sdk_content__']
        # potentially these might be used in the templates. These are not 
        # supplied in production so we will remove them and any others.
        del kwargs['__sdk_template__']
        del kwargs['__sdk_content__']

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
            for k in content:
                kwargs.setdefault(k, content[k])
            return template.render(**kwargs)

    def _dispatch_static(self, filename):
        static_file = os.path.join(self.static_path, filename)
        if not os.path.isfile(static_file):
            return abort(404)

        # scss support
        if filename.startswith('css/') and filename.endswith('.scss'):
            _scss = scss.Scss()
            css = _scss.compile(scss_file=static_file)
            res = make_response()
            res.data = css
            res.mimetype = 'text/css'
            return res

        # stylus support
        elif filename.startswith('css/') and filename.endswith('.styl'):
            css = compile_stylus(static_file)
            res = make_response()
            res.data = css
            res.mimetype = 'text/css'
            return res

        # less support
        elif filename.startswith('css/') and filename.endswith('.less'):
            css = compile_less(static_file)
            res = make_response()
            res.data = css
            res.mimetype = 'text/css'
            return res

        # coffeescript support
        elif filename.startswith('js/') and filename.endswith('.coffee'):
            cs_data = compile_coffeescript(static_file)
            res = make_response()
            res.data = cs_data
            res.mimetype = 'application/javascript'
            return res

        # everything else, straight served
        else:
            return send_from_directory(self.static_path, filename)

    def _dispatch_favicon(self,):
        return self._dispatch_static('favicon.ico')

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

