import logging
import os
import os.path
import sys

import markdown
import pyjade


path_name = os.path.dirname(sys.argv[0])
root_path = os.path.abspath(path_name)
node_path = os.path.join(root_path, 'node')
skeleton_path = os.path.join(root_path, 'skeletons')
routeless_path = os.path.join(root_path, 'sdklib', 'routeless')

conlog = logging.StreamHandler()
logger = logging.getLogger('console')
logger.addHandler(conlog)
logger.setLevel(logging.INFO)

# possible override for local development
API_ENDPOINT = os.environ.get(
    'MARKUPHIVE_API_ENDPOINT', 
    'https://api.markuphive.com'
)

@pyjade.register_filter('markdown')
def _filter_markdown(text, ast):
    return markdown.markdown(text, safe_mode='escape')
