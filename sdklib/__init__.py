import logging
import os
import os.path
import sys


path_name = os.path.dirname(sys.argv[0])
root_path = os.path.abspath(path_name)
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
