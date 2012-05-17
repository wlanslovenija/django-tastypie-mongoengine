import urlparse

from django.test import client

# Taken from https://code.djangoproject.com/attachment/ticket/17797/django-test-client-PATCH.patch

def requestfactory_patch(self, path, data={}, content_type=client.MULTIPART_CONTENT, **extra): 
    "Construct a PATCH request." 
     
    patch_data = self._encode_data(data, content_type) 

    parsed = urlparse.urlparse(path) 
    r = { 
        'CONTENT_LENGTH': len(patch_data), 
        'CONTENT_TYPE': content_type, 
        'PATH_INFO': self._get_path(parsed), 
        'QUERY_STRING': parsed[4], 
        'REQUEST_METHOD': 'PATCH', 
        'wsgi.input': client.FakePayload(patch_data), 
    }
    r.update(extra)
    return self.request(**r) 

def client_patch(self, path, data={}, content_type=client.MULTIPART_CONTENT, follow=False, **extra):
    """
    Send a resource to the server using PATCH.
    """
    response = super(Client, self).patch(path, data=data, content_type=content_type, **extra)
    if follow:
        response = self._handle_redirects(response, **extra)
    return response

if not hasattr(client.RequestFactory, 'patch'):
    client.RequestFactory.patch = requestfactory_patch

if not hasattr(client.Client, 'patch'):
    client.Client.patch = client_patch
