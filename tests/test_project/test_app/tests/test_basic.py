from __future__ import with_statement

import urlparse

from django.core import exceptions, urlresolvers
from django.test import client, utils
from django.utils import simplejson as json

import tastypie
from tastypie import authorization as tastypie_authorization

from tastypie_mongoengine import resources as tastypie_mongoengine_resources, test_runner

from test_project.test_app import documents
from test_project.test_app.api import resources

# TODO: Test set operations
# TODO: Test bulk operations
# TODO: Test ordering, filtering
# TODO: Use Tastypie's testcase class for tests?

@utils.override_settings(DEBUG=True)
class BasicTest(test_runner.MongoEngineTestCase):
    api_name = 'v1'
    c = client.Client()

    def resourceListURI(self, resource_name):
        return urlresolvers.reverse('api_dispatch_list', kwargs={'api_name': self.api_name, 'resource_name': resource_name})

    def resourcePK(self, resource_uri):
        match = urlresolvers.resolve(resource_uri)
        return match.kwargs['pk']

    def resourceDetailURI(self, resource_name, resource_pk):
        return urlresolvers.reverse('api_dispatch_detail', kwargs={'api_name': self.api_name, 'resource_name': resource_name, 'pk': resource_pk})

    def fullURItoAbsoluteURI(self, uri):
        scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)
        return urlparse.urlunsplit((None, None, path, query, fragment))

    def test_basic(self):
        # Testing POST

        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 1"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        person1_uri = response['location']

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1')
        self.assertEqual(response['optional'], None)

        # Covered by Tastypie
        response = self.c.post(self.resourceListURI('person'), '{"name": null}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        # Covered by Tastypie
        response = self.c.post(self.resourceListURI('person'), '{}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        # Covered by Tastypie
        response = self.c.post(self.resourceListURI('person'), '{"optional": "Optional"}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        # Covered by MongoEngine validation
        response = self.c.post(self.resourceListURI('person'), '{"name": []}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        # Covered by MongoEngine validation
        response = self.c.post(self.resourceListURI('person'), '{"name": {}}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 2", "optional": null}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 2", "optional": "Optional"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        person2_uri = response['location']

        response = self.c.get(person2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 2')
        self.assertEqual(response['optional'], 'Optional')

        # Tastypie ignores additional field
        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 3", "additional": "Additional"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        # Referenced resources can be matched through fields if they match uniquely
        response = self.c.post(self.resourceListURI('customer'), '{"person": {"name": "Person 1"}}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        customer1_uri = response['location']

        response = self.c.get(customer1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['person']['name'], 'Person 1')
        self.assertEqual(response['person']['optional'], None)
        self.assertEqual(response['person']['resource_uri'], self.fullURItoAbsoluteURI(person1_uri))

        person1_id = response['person']['id']

        # Referenced resources can be even updated at the same time
        response = self.c.post(self.resourceListURI('customer'), '{"person": {"id": "%s", "name": "Person 1 UPDATED"}}' % person1_id, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        customer2_uri = response['location']

        response = self.c.get(customer2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['person']['name'], 'Person 1 UPDATED')
        self.assertEqual(response['person']['optional'], None)
        self.assertEqual(response['person']['resource_uri'], self.fullURItoAbsoluteURI(person1_uri))
        self.assertEqual(response['employed'], False)

        response = self.c.post(self.resourceListURI('customer'), '{"person": "%s"}' % self.fullURItoAbsoluteURI(person1_uri), content_type='application/json')
        self.assertEqual(response.status_code, 201)

        customer3_uri = response['location']

        response = self.c.get(customer3_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['person']['name'], 'Person 1 UPDATED')
        self.assertEqual(response['person']['optional'], None)
        self.assertEqual(response['person']['resource_uri'], self.fullURItoAbsoluteURI(person1_uri))

        response = self.c.get(self.resourceListURI('person'))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['objects']), 4)

        # Referenced resources can also be created automatically
        response = self.c.post(self.resourceListURI('customer'), '{"person": {"name": "Person does not YET exist"}}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        customer4_uri = response['location']

        response = self.c.get(customer4_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['person']['name'], 'Person does not YET exist')
        self.assertEqual(response['person']['optional'], None)

        person5_uri = response['person']['resource_uri']

        response = self.c.get(person5_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person does not YET exist')
        self.assertEqual(response['optional'], None)

        response = self.c.get(self.resourceListURI('person'))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['objects']), 5)

        response = self.c.post(self.resourceListURI('embeddeddocumentfieldtest'), '{"customer": {"name": "Embedded person 1"}}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        embeddeddocumentfieldtest_uri = response['location']

        response = self.c.get(embeddeddocumentfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['customer']['name'], 'Embedded person 1')

        # Covered by MongoEngine validation
        response = self.c.post(self.resourceListURI('dictfieldtest'), '{"dictionary": {}}', content_type='application/json')
        self.assertContains(response, 'required and cannot be empty', status_code=400)

        # Covered by MongoEngine validation
        response = self.c.post(self.resourceListURI('dictfieldtest'), '{"dictionary": null}', content_type='application/json')
        self.assertContains(response, 'required and cannot be empty', status_code=400)

        # Covered by MongoEngine validation
        response = self.c.post(self.resourceListURI('dictfieldtest'), '{"dictionary": false}', content_type='application/json')
        self.assertContains(response, 'dictionaries may be used', status_code=400)

        response = self.c.post(self.resourceListURI('dictfieldtest'), '{"dictionary": {"a": "abc", "number": 34}}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        dictfieldtest_uri = response['location']

        response = self.c.get(dictfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['dictionary']['a'], 'abc')
        self.assertEqual(response['dictionary']['number'], 34)

        response = self.c.post(self.resourceListURI('listfieldtest'), '{"intlist": [1, 2, 3, 4], "stringlist": ["a", "b", "c"], "anytype": ["a", 1, null, 2]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        listfieldtest_uri = response['location']

        response = self.c.get(listfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['intlist'], [1, 2, 3, 4])
        self.assertEqual(response['stringlist'], ['a', 'b', 'c'])
        self.assertEqual(response['anytype'], ['a', 1, None, 2])

        # Field is not required
        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": []}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": [{"name": "Embedded person 1"}, {"name": "Embedded person 2", "hidden": "Should be hidden"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        embeddedlistfieldtest_uri = response['location']

        response = self.c.get(embeddedlistfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['embeddedlist'][0]['name'], 'Embedded person 1')
        self.assertEqual(response['embeddedlist'][1]['name'], 'Embedded person 2')
        self.assertTrue('hidden' not in response['embeddedlist'][1])
        self.assertEqual(len(response['embeddedlist']), 2)

        embeddedlistfieldtest_object = documents.EmbeddedListFieldTest.objects.get(pk=self.resourcePK(self.fullURItoAbsoluteURI(embeddedlistfieldtest_uri)))
        self.assertEqual(embeddedlistfieldtest_object.embeddedlist[1].hidden, None)

        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": ["%s"]}' % self.fullURItoAbsoluteURI(person1_uri), content_type='application/json')
        self.assertContains(response, 'was not given a dictionary-alike data', status_code=400)

        response = self.c.post(self.resourceListURI('embeddedlistfieldnonfulltest'), '{"embeddedlist": [{"name": "Embedded person 1"}, {"name": "Embedded person 2", "hidden": "Should be hidden"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        embeddedlistfieldnonfulltest_uri = response['location']

        response = self.c.get(embeddedlistfieldnonfulltest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['embeddedlist']), 2)

        for i, person_uri in enumerate(response['embeddedlist']):
            person = self.c.get(person_uri)
            self.assertEqual(person.status_code, 200)
            person = json.loads(person.content)

            self.assertEqual(person['name'], 'Embedded person %d' % (i + 1))
            self.assertTrue('hidden' not in person)

        embeddedlistfieldtest_object = documents.EmbeddedListFieldTest.objects.get(pk=self.resourcePK(self.fullURItoAbsoluteURI(embeddedlistfieldnonfulltest_uri)))
        self.assertEqual(embeddedlistfieldtest_object.embeddedlist[1].hidden, None)

        # Testing PUT

        response = self.c.put(person1_uri, '{"name": "Person 1z"}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        # Covered by Tastypie
        response = self.c.put(person1_uri, '{"name": null}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        # Covered by Tastypie
        response = self.c.put(person1_uri, '{}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        # Covered by Tastypie
        response = self.c.put(person1_uri, '{"optional": "Optional ZZZ"}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        # Covered by MongoEngine validation
        response = self.c.put(person1_uri, '{"name": []}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        # Covered by MongoEngine validation
        response = self.c.put(person1_uri, '{"name": {}}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1z')

        response = self.c.put(customer2_uri, '{"person": "%s"}' % self.fullURItoAbsoluteURI(person2_uri), content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(customer2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['person']['name'], 'Person 2')
        self.assertEqual(response['person']['optional'], 'Optional')

        response = self.c.put(embeddeddocumentfieldtest_uri, '{"customer": {"name": "Embedded person 1a"}}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embeddeddocumentfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['customer']['name'], 'Embedded person 1a')

        response = self.c.put(dictfieldtest_uri, '{"dictionary": {"a": 341, "number": "abcd"}}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(dictfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['dictionary']['number'], 'abcd')
        self.assertEqual(response['dictionary']['a'], 341)

        response = self.c.put(listfieldtest_uri, '{"intlist": [1, 2, 4], "stringlist": ["a", "b", "c", "d"], "anytype": [null, "1", 1]}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(listfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['intlist'], [1, 2, 4])
        self.assertEqual(response['stringlist'], ['a', 'b', 'c', 'd'])
        self.assertEqual(response['anytype'], [None, "1", 1])

        response = self.c.put(embeddedlistfieldtest_uri, '{"embeddedlist": [{"name": "Embedded person 1a"}, {"name": "Embedded person 2a"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embeddedlistfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['embeddedlist'][0]['name'], 'Embedded person 1a')
        self.assertEqual(response['embeddedlist'][1]['name'], 'Embedded person 2a')
        self.assertEqual(len(response['embeddedlist']), 2)

        response = self.c.put(embeddedlistfieldtest_uri, '{"embeddedlist": [{"name": "Embedded person 123"}, {}]}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        response = self.c.put(embeddedlistfieldnonfulltest_uri, '{"embeddedlist": [{"name": "Embedded person 1a"}, {"name": "Embedded person 2a"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embeddedlistfieldnonfulltest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['embeddedlist']), 2)

        for i, person_uri in enumerate(response['embeddedlist']):
            person = self.c.get(person_uri)
            self.assertEqual(person.status_code, 200)
            person = json.loads(person.content)

            self.assertEqual(person['name'], 'Embedded person %da' % (i + 1))

        # Testing PATCH

        response = self.c.patch(person1_uri, '{"name": "Person 1 PATCHED"}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        # Covered by Tastypie
        response = self.c.patch(person1_uri, '{"name": null}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        # Should not do anything, but succeed
        response = self.c.patch(person1_uri, '{}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        # Tastypie ignores additional field, should not do anything, but succeed
        response = self.c.patch(person1_uri, '{"additional": "Additional"}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        # Covered by Tastypie
        response = self.c.patch(person1_uri, '{"optional": "Optional PATCHED"}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        # Covered by MongoEngine validation
        response = self.c.patch(person1_uri, '{"name": []}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        # Covered by MongoEngine validation
        response = self.c.patch(person1_uri, '{"name": {}}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1 PATCHED')
        self.assertEqual(response['optional'], 'Optional PATCHED')

        response = self.c.patch(customer2_uri, '{"person": "%s"}' % self.fullURItoAbsoluteURI(person1_uri), content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(customer2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        
        self.assertEqual(response['person']['name'], 'Person 1 PATCHED')
        self.assertEqual(response['person']['optional'], 'Optional PATCHED')

        self.assertEqual(response['employed'], False)

        # There is a bug in Tastypie, so we test only on versions which have it fixed
        # https://github.com/toastdriven/django-tastypie/issues/501
        # https://github.com/toastdriven/django-tastypie/commit/e4de9377cb
        if tastypie.__version__ > (0, 9, 11):
            response = self.c.patch(customer2_uri, '{"employed": true}', content_type='application/json')
            self.assertEqual(response.status_code, 202)

            response = self.c.get(customer2_uri)
            self.assertEqual(response.status_code, 200)
            response = json.loads(response.content)

            self.assertEqual(response['employed'], True)

        response = self.c.patch(embeddeddocumentfieldtest_uri, '{"customer": {"name": "Embedded person PATCHED"}}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(embeddeddocumentfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['customer']['name'], 'Embedded person PATCHED')

        response = self.c.patch(dictfieldtest_uri, '{"dictionary": {"a": 42}}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(dictfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['dictionary']['a'], 42)
        self.assertTrue('number' not in response['dictionary'])

        response = self.c.patch(listfieldtest_uri, '{"intlist": [1, 2, 42]}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(listfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['intlist'], [1, 2, 42])
        self.assertEqual(response['stringlist'], ['a', 'b', 'c', 'd'])
        self.assertEqual(response['anytype'], [None, "1", 1])

        response = self.c.patch(embeddedlistfieldtest_uri, '{"embeddedlist": [{"name": "Embedded person PATCHED"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(embeddedlistfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['embeddedlist'][0]['name'], 'Embedded person PATCHED')
        self.assertEqual(len(response['embeddedlist']), 1)

        # Testing DELETE

        response = self.c.delete(person1_uri)
        self.assertEqual(response.status_code, 204)

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 404)

    def test_objectclass(self):
        response = self.c.get(self.resourceListURI('personobjectclass'))

        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertEqual(len(response['objects']), 0)

        response = self.c.post(self.resourceListURI('personobjectclass'), '{"name": "Person 1"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        person1_uri = response['location']

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1')
        self.assertEqual(response['optional'], None)

    def test_schema(self):
        embeddeddocumentfieldtest_schema_uri = self.resourceListURI('embeddeddocumentfieldtest') + 'schema/'

        response = self.c.get(embeddeddocumentfieldtest_schema_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['fields']), 3)
        self.assertEqual(len(response['fields']['customer']['embedded']['fields']), 3)
        self.assertTrue('name' in response['fields']['customer']['embedded']['fields'])
        self.assertTrue('optional' in response['fields']['customer']['embedded']['fields'])
        self.assertTrue('resource_type' in response['fields']['customer']['embedded']['fields'])

        customer_schema_uri = self.resourceListURI('customer') + 'schema/'

        response = self.c.get(customer_schema_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['fields']), 4)
        self.assertEqual(response['fields']['person']['reference_uri'], self.resourceListURI('person'))

        listfieldtest_schema_uri = self.resourceListURI('listfieldtest') + 'schema/'

        response = self.c.get(listfieldtest_schema_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['fields']), 6)
        self.assertEqual(response['fields']['intlist']['content']['type'], 'int')
        self.assertEqual(response['fields']['stringlist']['content']['type'], 'string')
        self.assertTrue('content' not in response['fields']['anytype'])

        embeddedlistfieldtest_schema_uri = self.resourceListURI('embeddedlistfieldtest') + 'schema/'

        response = self.c.get(embeddedlistfieldtest_schema_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['fields']), 3)
        self.assertEqual(len(response['fields']['embeddedlist']['embedded']['fields']), 4)
        self.assertTrue('name' in response['fields']['embeddedlist']['embedded']['fields'])
        self.assertTrue('optional' in response['fields']['embeddedlist']['embedded']['fields'])
        self.assertTrue('resource_uri' in response['fields']['embeddedlist']['embedded']['fields'])
        self.assertTrue('resource_type' in response['fields']['embeddedlist']['embedded']['fields'])

        self.assertEqual(len(response['fields']['embeddedlist']['embedded']['resource_types']), 2)
        self.assertTrue('person' in response['fields']['embeddedlist']['embedded']['resource_types'])
        self.assertTrue('strangeperson' in response['fields']['embeddedlist']['embedded']['resource_types'])

        referencedlistfieldtest_schema_uri = self.resourceListURI('referencedlistfieldtest') + 'schema/'

        response = self.c.get(referencedlistfieldtest_schema_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['fields']), 3)
        self.assertTrue('reference_schema' in response['fields']['referencedlist'])
        self.assertTrue('reference_uri' in response['fields']['referencedlist'])

    def test_invalid(self):
        # Invalid ObjectId
        response = self.c.get(self.resourceListURI('customer') + 'foobar/')
        self.assertEqual(response.status_code, 404)

    def test_embeddedlist(self):
        # Testing POST

        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": [{"name": "Embedded person 1"}, {"name": "Embedded person 2", "optional": "Optional"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        mainresource_uri = response['location']

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['embeddedlist'][0]['name'], 'Embedded person 1')
        self.assertEqual(response['embeddedlist'][0]['optional'], None)
        self.assertEqual(response['embeddedlist'][1]['name'], 'Embedded person 2')
        self.assertEqual(response['embeddedlist'][1]['optional'], 'Optional')
        self.assertEqual(len(response['embeddedlist']), 2)

        embedded1_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/0/'

        response = self.c.get(embedded1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 1')
        self.assertEqual(response['optional'], None)
        self.assertEqual(response['resource_uri'], embedded1_uri)

        embedded2_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/1/'

        response = self.c.get(embedded2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 2')
        self.assertEqual(response['optional'], 'Optional')
        self.assertEqual(response['resource_uri'], embedded2_uri)

        embedded3_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/2/'

        response = self.c.get(embedded3_uri)
        self.assertEqual(response.status_code, 404)

        embeddedresource_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/'

        response = self.c.get(embeddedresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['name'], 'Embedded person 1')
        self.assertEqual(response['objects'][0]['optional'], None)
        self.assertEqual(response['objects'][0]['resource_uri'], embedded1_uri)
        self.assertEqual(response['objects'][1]['name'], 'Embedded person 2')
        self.assertEqual(response['objects'][1]['optional'], 'Optional')
        self.assertEqual(response['objects'][1]['resource_uri'], embedded2_uri)

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 3"}', content_type='application/json')
        self.assertRedirects(response, embedded3_uri, status_code=201)

        response = self.c.get(embedded3_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 3')
        self.assertEqual(response['optional'], None)
        self.assertEqual(response['resource_uri'], embedded3_uri)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['embeddedlist']), 3)

        embedded4_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/3/'

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 4", "optional": 42}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 4", "optional": []}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 4", "optional": {}}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        response = self.c.get(embedded4_uri)
        self.assertEqual(response.status_code, 404)

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 4", "optional": "Foobar"}', content_type='application/json')
        self.assertRedirects(response, embedded4_uri, status_code=201)

        response = self.c.get(embedded4_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 4')
        self.assertEqual(response['optional'], 'Foobar')
        self.assertEqual(response['resource_uri'], embedded4_uri)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['embeddedlist']), 4)

        # Testing PUT

        response = self.c.put(embedded4_uri, '{"name": "Embedded person 4a", "optional": "Foobar PUT"}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embedded4_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 4a')
        self.assertEqual(response['optional'], 'Foobar PUT')
        self.assertEqual(response['resource_uri'], embedded4_uri)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['embeddedlist'][3]['name'], 'Embedded person 4a')
        self.assertEqual(response['embeddedlist'][3]['optional'], 'Foobar PUT')
        self.assertEqual(len(response['embeddedlist']), 4)

        response = self.c.put(embedded4_uri, '{"name": "Embedded person 4a", "optional": []}', content_type='application/json')
        self.assertContains(response, 'only accepts string values', status_code=400)

        response = self.c.put(embedded4_uri, '{}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        response = self.c.put(embedded4_uri, '{"optional": "Optional"}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

        response = self.c.put(embedded4_uri, '{"name": "Embedded person 4 ZZZ"}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embedded4_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 4 ZZZ')
        self.assertEqual(response['optional'], None)
        self.assertEqual(response['resource_uri'], embedded4_uri)

        response = self.c.put(embedded1_uri, '{"name": "Embedded person 1 ZZZ"}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embedded1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 1 ZZZ')
        self.assertEqual(response['optional'], None)
        self.assertEqual(response['resource_uri'], embedded1_uri)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['embeddedlist']), 4)

        # Testing PATCH

        response = self.c.patch(embedded1_uri, '{"name": "Embedded person 1 PATCHED"}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(embedded1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 1 PATCHED')
        self.assertEqual(response['optional'], None)
        self.assertEqual(response['resource_uri'], embedded1_uri)

        # Testing DELETE

        response = self.c.delete(embedded4_uri)
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embedded4_uri)
        self.assertEqual(response.status_code, 404)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['embeddedlist']), 3)

        response = self.c.get(embedded2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 2')
        self.assertEqual(response['optional'], 'Optional')
        self.assertEqual(response['resource_uri'], embedded2_uri)

        response = self.c.delete(embedded2_uri)
        self.assertEqual(response.status_code, 204)

        response = self.c.get(embedded2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        # Content from embedded3_uri moves in place of embedded2_uri
        self.assertEqual(response['name'], 'Embedded person 3')
        self.assertEqual(response['optional'], None)
        self.assertEqual(response['resource_uri'], embedded2_uri)

        response = self.c.get(embedded3_uri)
        self.assertEqual(response.status_code, 404)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['embeddedlist']), 2)

    def test_referencedlist(self):
        response = self.c.get(self.resourceListURI('referencedlistfieldtest'))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['objects']), 0)

        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 1"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        person1_uri = response['location']

        response = self.c.post(self.resourceListURI('referencedlistfieldtest'), '{"referencedlist": ["' + self.fullURItoAbsoluteURI(person1_uri) + '", {"name": "Person 2", "hidden": "Should be hidden"}, {"name": "Person 3", "optional": "Optional"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        mainresource_uri = response['location']

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['referencedlist']), 3)
        for i, person in enumerate(response['referencedlist']):
            self.assertEqual(person['resource_type'], 'person')
            self.assertEqual(person['name'], 'Person %d' % (i + 1))
            self.assertTrue('hidden' not in person)

        self.assertEqual(response['referencedlist'][2]['optional'], 'Optional')

        referencedlistfieldtest_object = documents.ReferencedListFieldTest.objects.get(pk=self.resourcePK(self.fullURItoAbsoluteURI(mainresource_uri)))
        self.assertEqual(referencedlistfieldtest_object.referencedlist[1].hidden, None)

        person2, person3 = response['referencedlist'][1:]

        response = self.c.put(person2['resource_uri'], '{"name": "Person 2", "optional": "Foobar PUT"}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(person2['resource_uri'])
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 2')
        self.assertEqual(response['optional'], 'Foobar PUT')

        response = self.c.put(mainresource_uri, '{"referencedlist": ["' + person2['resource_uri'] + '", "' + person3['resource_uri'] + '"]}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['referencedlist']), 2)
        for i, person in enumerate(response['referencedlist']):
            self.assertEqual(person['name'], 'Person %i' % (i + 2))

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1')

    def test_referencedlistnonfull(self):
        response = self.c.get(self.resourceListURI('referencedlistfieldnonfulltest'))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['objects']), 0)

        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 1"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        person1_uri = response['location']

        response = self.c.post(self.resourceListURI('referencedlistfieldnonfulltest'), '{"referencedlist": ["' + self.fullURItoAbsoluteURI(person1_uri) + '", {"name": "Person 2", "hidden": "Should be hidden"}, {"name": "Person 3", "optional": "Optional"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        mainresource_uri = response['location']

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['referencedlist']), 3)
        for i, person_uri in enumerate(response['referencedlist']):
            person = self.c.get(person_uri)
            self.assertEqual(person.status_code, 200)
            person = json.loads(person.content)

            self.assertEqual(person['resource_type'], 'person')
            self.assertEqual(person['name'], 'Person %d' % (i + 1))
            self.assertTrue('hidden' not in person)

        referencedlistfieldtest_object = documents.ReferencedListFieldTest.objects.get(pk=self.resourcePK(self.fullURItoAbsoluteURI(mainresource_uri)))
        self.assertEqual(referencedlistfieldtest_object.referencedlist[1].hidden, None)

        person2_uri, person3_uri = response['referencedlist'][1:]

        response = self.c.put(person2_uri, '{"name": "Person 2", "optional": "Foobar PUT"}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(person2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 2')
        self.assertEqual(response['optional'], 'Foobar PUT')

        response = self.c.put(mainresource_uri, '{"referencedlist": ["' + person2_uri + '", "' + person3_uri + '"]}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['referencedlist']), 2)
        for i, person_uri in enumerate(response['referencedlist']):
            person = self.c.get(person_uri)
            self.assertEqual(person.status_code, 200)
            person = json.loads(person.content)

            self.assertEqual(person['name'], 'Person %i' % (i + 2))

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1')

    def test_polymorphic_schema(self):
        person_schema_uri = self.resourceListURI('person') + 'schema/'

        response = self.c.get(person_schema_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['fields']), 5)
        self.assertTrue('resource_type' in response['fields'])
        self.assertTrue('strange' not in response['fields'])
        self.assertEqual(len(response['resource_types']), 2)
        self.assertTrue('person' in response['resource_types'])
        self.assertTrue('strangeperson' in response['resource_types'])

        response = self.c.get(person_schema_uri, {'type': 'strangeperson'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['fields']), 6)
        self.assertTrue('resource_type' in response['fields'])
        self.assertTrue('strange' in response['fields'])
        self.assertEqual(len(response['resource_types']), 2)
        self.assertTrue('person' in response['resource_types'])
        self.assertTrue('strangeperson' in response['resource_types'])

    def test_polymorphic(self):
        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 1"}', content_type='application/json; type=person')
        self.assertEqual(response.status_code, 201)

        # Tastypie ignores additional field
        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 1z", "strange": "Foobar"}', content_type='application/json; type=person')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 2", "strange": "Foobar"}', content_type='application/json; type=strangeperson')
        self.assertEqual(response.status_code, 201)

        # Field "name" is required
        response = self.c.post(self.resourceListURI('person'), '{"strange": "Foobar"}', content_type='application/json; type=strangeperson')
        self.assertContains(response, 'field has no data', status_code=400)

        # Field "strange" is required
        response = self.c.post(self.resourceListURI('person'), '{"name": "Person 2"}', content_type='application/json; type=strangeperson')
        self.assertContains(response, 'field has no data', status_code=400)

        response = self.c.get(self.resourceListURI('person'))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['objects']), 3)
        self.assertEqual(response['objects'][0]['name'], 'Person 1')
        self.assertEqual(response['objects'][0]['resource_type'], 'person')
        self.assertEqual(response['objects'][1]['name'], 'Person 1z')
        self.assertEqual(response['objects'][1]['resource_type'], 'person')
        self.assertEqual(response['objects'][2]['name'], 'Person 2')
        self.assertEqual(response['objects'][2]['strange'], 'Foobar')
        self.assertEqual(response['objects'][2]['resource_type'], 'strangeperson')

        person1_uri = response['objects'][0]['resource_uri']
        person2_uri = response['objects'][2]['resource_uri']

        response = self.c.put(person1_uri, '{"name": "Person 1a"}', content_type='application/json; type=person')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1a')

        # Changing existing resource type (type->subtype)

        # Field "name" is required
        response = self.c.put(person1_uri, '{"strange": "something"}', content_type='application/json; type=strangeperson')
        self.assertContains(response, 'field has no data', status_code=400)

        # Field "strange" is required
        response = self.c.put(person1_uri, '{"name": "Person 1a"}', content_type='application/json; type=strangeperson')
        self.assertContains(response, 'field has no data', status_code=400)

        response = self.c.put(person1_uri, '{"name": "Person 1a", "strange": "something"}', content_type='application/json; type=strangeperson')
        # Object got replaced, so we get 201 with location, but we do not want a
        # new object, so redirect should match initial resource URL
        self.assertRedirects(response, person1_uri, status_code=201)

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1a')
        self.assertEqual(response['strange'], 'something')
        self.assertEqual(response['resource_type'], 'strangeperson')

        response = self.c.put(person2_uri, '{"name": "Person 2a", "strange": "FoobarXXX"}', content_type='application/json; type=strangeperson')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(person2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 2a')
        self.assertEqual(response['strange'], 'FoobarXXX')

        # Changing resource type again (subtype->type)
        response = self.c.put(person1_uri, '{"name": "Person 1c"}', content_type='application/json; type=person')
        self.assertRedirects(response, person1_uri, status_code=201)

        response = self.c.get(person1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 1c')
        self.assertEqual(response['resource_type'], 'person')

        response = self.c.put(person2_uri, '{"name": "Person 2c", "strange": "something"}', content_type='application/json; type=person')
        # Additional fields are ignored
        self.assertRedirects(response, person2_uri, status_code=201)

        response = self.c.get(person2_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Person 2c')
        self.assertEqual(response['resource_type'], 'person')

        # TODO: Test PATCH
        # TODO: Test DELETE

    def test_embeddedlist_polymorphic(self):
        # Testing POST

        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": [{"name": "Embedded person 1"}, {"name": "Embedded person 2", "optional": "Optional"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        mainresource_uri = response['location']

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['embeddedlist'][0]['name'], 'Embedded person 1')
        self.assertEqual(response['embeddedlist'][0]['optional'], None)
        self.assertEqual(response['embeddedlist'][0]['resource_type'], 'person')
        self.assertEqual(response['embeddedlist'][1]['name'], 'Embedded person 2')
        self.assertEqual(response['embeddedlist'][1]['optional'], 'Optional')
        self.assertEqual(response['embeddedlist'][0]['resource_type'], 'person')
        self.assertEqual(len(response['embeddedlist']), 2)

        embeddedresource_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/'
        embedded3_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/2/'

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 3"}', content_type='application/json; type=strangeperson')
        self.assertContains(response, 'field has no data', status_code=400)

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 3", "strange": "Strange"}', content_type='application/json; type=strangeperson')
        self.assertRedirects(response, embedded3_uri, status_code=201)

        response = self.c.get(embedded3_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 3')
        self.assertEqual(response['strange'], 'Strange')
        self.assertEqual(response['resource_type'], 'strangeperson')

        # TODO: Test PUT
        # TODO: Test PATCH
        # TODO: Test DELETE

    def test_limited_polymorphic(self):
        response = self.c.post(self.resourceListURI('onlysubtypeperson'), '{"name": "Person 1", "strange": "Strange"}', content_type='application/json; type=strangeperson')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('onlysubtypeperson'), '{"name": "Person 1"}', content_type='application/json; type=person')
        self.assertContains(response, 'Invalid object type', status_code=400)

        response = self.c.post(self.resourceListURI('onlysubtypeperson'), '{"name": "Person 1"}', content_type='application/json')
        self.assertContains(response, 'Invalid object type', status_code=400)

    def test_polymorphic_duplicate_class(self):
        with self.assertRaises(exceptions.ImproperlyConfigured):
            class DuplicateSubtypePersonResource(tastypie_mongoengine_resources.MongoEngineResource):
                class Meta:
                    queryset = documents.Person.objects.all()
                    allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
                    authorization = tastypie_authorization.Authorization()

                    polymorphic = {
                        'strangeperson': resources.StrangePersonResource,
                        'otherstrangeperson': resources.OtherStrangePersonResource,
                    }

    def test_mapping_boolean_field(self):
        self.assertEqual(resources.BooleanMapTestResource().is_published_auto.default, documents.BooleanMapTest()._fields['is_published_auto'].default)
        self.assertEqual(resources.BooleanMapTestResource().is_published_auto.null, not documents.BooleanMapTest()._fields['is_published_auto'].required)
        self.assertEqual(resources.BooleanMapTestResource().is_published_defined.default, documents.BooleanMapTest()._fields['is_published_defined'].default)
        self.assertEqual(resources.BooleanMapTestResource().is_published_defined.null, not documents.BooleanMapTest()._fields['is_published_defined'].required)
        self.assertEqual(resources.BooleanMapTestResource().is_published_auto.default, resources.BooleanMapTestResource().is_published_defined.default)
        self.assertEqual(resources.BooleanMapTestResource().is_published_auto.null, resources.BooleanMapTestResource().is_published_defined.null)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{"is_published_auto": true}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{"is_published_defined": true}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{"is_published_auto": true, "is_published_defined": true}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{"is_published_auto": false}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{"is_published_defined": false}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{"is_published_auto": false, "is_published_defined": true}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        response = self.c.post(self.resourceListURI('booleanmaptest'), '{"is_published_auto": true, "is_published_defined": false}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_embeddedlist_with_flag(self):
        response = self.c.post(self.resourceListURI('embeddedlistwithflagfieldtest'), '{"embeddedlist": [{"name": "Embedded person 1"}, {"name": "Embedded person 2", "optional": "Optional"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        mainresource_uri = response['location']
        embeddedresource_uri = self.fullURItoAbsoluteURI(mainresource_uri) + 'embeddedlist/'

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['is_published'], False)

        response = self.c.post(embeddedresource_uri, '{"name": "Embedded person 1", "strange": "Strange"}', content_type='application/json; type=strangeperson')
        self.assertEqual(response.status_code, 201)

        response = self.c.patch(mainresource_uri, '{"is_published": true}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(mainresource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['is_published'], True)

    def test_nested_lists_field(self):
        posts = """
        {
            "posts": [
                {
                    "title": "Embedded post 1",
                    "comments": [
                        {"content": "Embedded comment 1.1"},
                        {"content": "Embedded comment 1.2"}
                    ]
                },
                {
                    "title": "Embedded post 2",
                    "comments": [
                        {"content": "Embedded comment 2.1"},
                        {"content": "Embedded comment 2.2"}
                    ]
                }
            ]
        }
        """

        response = self.c.post(self.resourceListURI('board'), posts, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        board_uri = response['location']

        response = self.c.get(board_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['posts'][0]['comments'][0]['content'], 'Embedded comment 1.1')
        self.assertEqual(response['posts'][1]['comments'][0]['content'], 'Embedded comment 2.1')

        response = self.c.get(board_uri + 'posts/', {'order_by': 'title'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['title'], 'Embedded post 1')
        self.assertEqual(response['objects'][1]['title'], 'Embedded post 2')

        response = self.c.get(board_uri + 'posts/', {'order_by': '-title'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['title'], 'Embedded post 2')
        self.assertEqual(response['objects'][1]['title'], 'Embedded post 1')

        response = self.c.get(board_uri + 'posts/', {'order_by': 'comments__content'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['title'], 'Embedded post 1')
        self.assertEqual(response['objects'][1]['title'], 'Embedded post 2')

        response = self.c.get(board_uri + 'posts/', {'order_by': '-comments__content'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['title'], 'Embedded post 2')
        self.assertEqual(response['objects'][1]['title'], 'Embedded post 1')

    def test_ordering(self):
        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": [{"name": "Embedded person 1"}, {"name": "Embedded person 2", "optional": "Optional"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        mainresource1_uri = response['location']

        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": [{"name": "Embedded person 1a"}, {"name": "Embedded person 2a", "optional": "Optional"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        mainresource2_uri = response['location']

        # MongoDB IDs are monotonic so this will sort it in the creation order
        response = self.c.get(self.resourceListURI('embeddedlistfieldtest'), {'order_by': 'id'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['resource_uri'], self.fullURItoAbsoluteURI(mainresource1_uri))
        self.assertEqual(response['objects'][1]['resource_uri'], self.fullURItoAbsoluteURI(mainresource2_uri))

        # MongoDB IDs are monotonic so this will sort it in reverse of the creation order
        response = self.c.get(self.resourceListURI('embeddedlistfieldtest'), {'order_by': '-id'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['resource_uri'], self.fullURItoAbsoluteURI(mainresource2_uri))
        self.assertEqual(response['objects'][1]['resource_uri'], self.fullURItoAbsoluteURI(mainresource1_uri))

        embeddedresource1_uri = self.fullURItoAbsoluteURI(mainresource1_uri) + 'embeddedlist/'
        embedded1_uri = self.fullURItoAbsoluteURI(mainresource1_uri) + 'embeddedlist/0/'
        embedded2_uri = self.fullURItoAbsoluteURI(mainresource1_uri) + 'embeddedlist/1/'

        response = self.c.get(embeddedresource1_uri, {'order_by': 'name'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['resource_uri'], embedded1_uri)
        self.assertEqual(response['objects'][1]['resource_uri'], embedded2_uri)

        response = self.c.get(embeddedresource1_uri, {'order_by': '-name'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['resource_uri'], embedded2_uri)
        self.assertEqual(response['objects'][1]['resource_uri'], embedded1_uri)

        response = self.c.get(self.resourceListURI('embeddedlistfieldtest'), {'order_by': 'embeddedlist__name'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['resource_uri'], self.fullURItoAbsoluteURI(mainresource1_uri))
        self.assertEqual(response['objects'][1]['resource_uri'], self.fullURItoAbsoluteURI(mainresource2_uri))

        response = self.c.get(self.resourceListURI('embeddedlistfieldtest'), {'order_by': '-embeddedlist__name'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['objects'][0]['resource_uri'], self.fullURItoAbsoluteURI(mainresource2_uri))
        self.assertEqual(response['objects'][1]['resource_uri'], self.fullURItoAbsoluteURI(mainresource1_uri))

    def _test_pagination(self, uri, key, pattern):
        for i in range(100):
            response = self.c.post(uri, '{"%s": "%s"}' % (key, pattern % i), content_type='application/json')
            self.assertEqual(response.status_code, 201)

        response = self.c.get(uri, {'offset': '42', 'limit': 7})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['meta']['total_count'], 100)
        self.assertEqual(response['meta']['offset'], 42)
        self.assertEqual(response['meta']['limit'], 7)
        self.assertEqual(len(response['objects']), 7)

        for i, obj in enumerate(response['objects']):
            self.assertEqual(obj[key], pattern % (42 + i))

        offset = response['objects'][0]['id']

        response = self.c.get(uri, {'offset': offset, 'limit': 7})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['meta']['total_count'], 100)
        self.assertEqual(response['meta']['offset'], offset)
        self.assertEqual(response['meta']['limit'], 7)
        self.assertEqual(len(response['objects']), 7)

        for i, obj in enumerate(response['objects']):
            self.assertEqual(obj[key], pattern % (42 + i))

        response = self.c.get(uri, {'offset': offset, 'limit': -7})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['meta']['total_count'], 100)
        self.assertEqual(response['meta']['offset'], offset)
        self.assertEqual(response['meta']['limit'], -7)
        self.assertEqual(len(response['objects']), 7)

        for i, obj in enumerate(response['objects']):
            self.assertEqual(obj[key], pattern % (42 - i))

    def test_pagination(self):
        self._test_pagination(self.resourceListURI('person'), 'name', 'Person %s')

    def test_embedded_in_embedded_doc(self):
        post = """
        {
            "post": {
                "title": "Embedded post",
                "comments": [
                    {"content": "Embedded comment 1"},
                    {"content": "Embedded comment 2"}
                ]
            }
        }
        """

        response = self.c.post(self.resourceListURI('embeddedlistinembeddeddoctest'), post, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        post_uri = response['location']

        response = self.c.get(post_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(len(response['post']['comments']), 2)
        self.assertTrue('resource_uri' not in response['post'])
        self.assertTrue('resource_uri' not in response['post']['comments'][0])

    def test_field_auto_allocation(self):
        response = self.c.post(self.resourceListURI('autoallocationfieldtest'), '{"name": "Auto slug test !"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        resource_uri = response['location']

        response = self.c.get(resource_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['slug'], u'auto-slug-test')

    def test_embedded_document_custom_id(self):
        response = self.c.post(self.resourceListURI('documentwithid'), '{"title": "Main document"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        document_uri = response['location']

        response = self.c.get(document_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['title'], 'Main document')
        self.assertEqual(response['comments'], [])

        response = self.c.post(document_uri + 'comments/', '{"content": "Content"}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        comment_uri = response['location']

        response = self.c.get(comment_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['content'], 'Content')

        response = self.c.patch(comment_uri, '{"content": "Content 2"}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(comment_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['content'], 'Content 2')

        response = self.c.get(document_uri + 'comments/abcd/')
        self.assertEqual(response.status_code, 404)

        response = self.c.patch(document_uri + 'comments/abcd/', '{"content": "Content 2"}', content_type='application/json')
        self.assertEqual(response.status_code, 404)

        response = self.c.delete(comment_uri)
        self.assertEqual(response.status_code, 204)

        self._test_pagination(document_uri + 'comments/', 'content', 'Comment %s')
