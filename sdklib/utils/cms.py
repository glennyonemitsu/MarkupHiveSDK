'''
helper functions to query the CMS. These are all interfacing with the live 
account CMS data.
'''
from sdklib.utils.general import api_parse


class CMSUtil(object):
    '''
    This is the util class sent to the templates as the object 'cms' to 
    provide the cms query interface. Behind the scenes this uses the API
    '''

    def __init__(self, api):
        '''
        api = sdklib.api.MarkupHive instance
        '''
        self.api = api

    def content_types(self):
        return self.call('get_cms_content_types')

    def entries(self, type_name, page=0, limit=10, timestamp='', timezone='UTC', tags='', status='Published'):
        return self.call('get_cms_entries', type_name, page, limit, timestamp, timezone, tags, status=status)
        
    def entry(self, slug=None, uuid=None, status='Published'):
        return self.call('get_cms_entry', slug=slug, uuid=uuid, status=status)

    def call(self, method, *args, **kwargs):
        if self.api is None:
            return None
        else:
            result = getattr(self.api, method)(*args, **kwargs)
            return result['result']
