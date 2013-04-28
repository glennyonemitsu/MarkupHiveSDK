'''
API calls for andpoints starting with /application/ (sans version)
'''
from sdklib.api import call


def put_application(app_data, payload):
    name = app_data['application_name']
    uri = '/v0/application/{name}/'.format(name=name)
    return call('PUT', uri, payload, app_data)


