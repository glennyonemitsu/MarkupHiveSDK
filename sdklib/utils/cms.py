'''
helper functions to query the CMS. These are all interfacing with the live 
account CMS data.
'''
from sdklib.utils.general import api_parse


class CMSUtil(object):

    def __init__(self, api):
        '''
        api = sdklib.api.MarkupHive instance
        '''
        self.api = api

    def content_types(self):
        return self.call('get_cms_content_types')

    def entries(self, type_name, page=0, limit=10, timestamp=[], tags=[]):
        return self.call('get_cms_entries', type_name, page, limit, timestamp, tags)

    def call(self, method, *args, **kwargs):
        if self.api is None:
            return None
        else:
            return getattr(self.api, method)(*args, **kwargs)
