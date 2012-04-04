from django.utils import unittest
from django.test.client import Client

from . import documents

class SimpleTest(unittest.TestCase):
    apiUrl = '/api/v1/'
    c = Client()
    
    def setUp(self):
        documents.Person.drop_collection()
        documents.Customer.drop_collection()
        documents.EmbededDocumentFieldTest.drop_collection()
        documents.DictFieldTest.drop_collection()
        documents.ListFieldTest.drop_collection()
        documents.EmbeddedListFieldTest.drop_collection()
    
    def makeUrl(self, link):
        return self.apiUrl + link + "/"
    
    def getUri(self, location):
        """
        Gets resource_uri from response location.
        """
        return self.apiUrl + location.split(self.apiUrl)[1]

    def test_creating_content(self):
        from django.conf import settings
        settings.DEBUG = True
    
        response = self.c.post(self.makeUrl('person'), '{"name": "Person 1"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        response = self.c.post(self.makeUrl('person'), '{"name": "Person 2"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        response = self.c.post(self.makeUrl('customer'), '{"person": "%s"}' % self.getUri(response['location']), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        response = self.c.post(self.makeUrl('embededdocumentfieldtest'), '{"customer": {"name": "Embeded person 1"}}', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        response = self.c.post(self.makeUrl('dictfieldtest'), '{"dictionary": {"a": "abc", "number": 34}}', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        response = self.c.post(self.makeUrl('listfieldtest'), '{"intlist": [1, 2, 3, 4], "stringlist": ["a", "b", "c"]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        response = self.c.post(self.makeUrl('embeddedsortedlistfieldtest'), '{"embeddedlist": [{"name": "Embeded person 1"}, {"name": "Embeded person 2"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        