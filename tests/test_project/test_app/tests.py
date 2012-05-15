from django import test
from django.test import client, utils
from django.utils import simplejson as json, unittest

from test_project.test_app import documents

@utils.override_settings(DEBUG=True)
class SimpleTest(test.TestCase):
    apiUrl = '/api/v1/'
    c = client.Client()
    
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

    def test_polymorphic(self):
        response = self.c.post(self.makeUrl('person'), '{"name": "Person 1"}', content_type='application/json; type=person')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.makeUrl('person'), '{"name": "Person 2", "strange": "Foobar"}', content_type='application/json; type=strangeperson')
        self.assertEqual(response.status_code, 201)

        response = self.c.get(self.makeUrl('person'), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['objects']), 2)
        self.assertEqual(response['objects'][0]['name'], 'Person 1')
        self.assertEqual(response['objects'][0]['resource_type'], 'person')
        self.assertEqual(response['objects'][1]['name'], 'Person 2')
        self.assertEqual(response['objects'][1]['strange'], 'Foobar')
        self.assertEqual(response['objects'][1]['resource_type'], 'strangeperson')

        person1_uri = response['objects'][0]['resource_uri']
        person2_uri = response['objects'][1]['resource_uri']

        response = self.c.put(person1_uri, '{"name": "Person 1a"}', content_type='application/json; type=person')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(person1_uri, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1a')

        # It is impossible to change type to a subtype of existing object
        response = self.c.put(person1_uri, '{"name": "Person 1"}', content_type='application/json; type=strangeperson')
        self.assertEqual(response.status_code, 500)

        response = self.c.put(person2_uri, '{"name": "Person 2a", "strange": "FoobarXXX"}', content_type='application/json; type=strangeperson')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(person2_uri, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 2a')
        self.assertEqual(response['strange'], 'FoobarXXX')
