import urlparse

from django.core import urlresolvers
from django.test import client, utils
from django.utils import simplejson as json, unittest

from test_project import test_runner
from test_project.test_app import documents

# TODO: Test set operations
# TODO: Test bulk operations
# TODO: Test ordering, filtering

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

        response = self.c.post(self.resourceListURI('customer'), '{"person": "%s"}' % self.fullURItoAbsoluteURI(person1_uri), content_type='application/json')
        self.assertEqual(response.status_code, 201)

        customer_uri = response['location']

        response = self.c.get(customer_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['person']['name'], 'Person 1')
        self.assertEqual(response['person']['optional'], None)

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

        # Covered by Tastypie
        response = self.c.post(self.resourceListURI('dictfieldtest'), '{"dictionary": null}', content_type='application/json')
        self.assertContains(response, 'field has no data', status_code=400)

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

        response = self.c.post(self.resourceListURI('listfieldtest'), '{"intlist": [1, 2, 3, 4], "stringlist": ["a", "b", "c"]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        listfieldtest_uri = response['location']

        response = self.c.get(listfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['intlist'], [1, 2, 3, 4])
        self.assertEqual(response['stringlist'], ['a', 'b', 'c'])

        response = self.c.post(self.resourceListURI('embeddedlistfieldtest'), '{"embeddedlist": [{"name": "Embedded person 1"}, {"name": "Embedded person 2"}]}', content_type='application/json')
        self.assertEqual(response.status_code, 201)

        embeddedlistfieldtest_uri = response['location']

        response = self.c.get(embeddedlistfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['embeddedlist'][0]['name'], 'Embedded person 1')
        self.assertEqual(response['embeddedlist'][1]['name'], 'Embedded person 2')
        self.assertEqual(len(response['embeddedlist']), 2)

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

        response = self.c.put(customer_uri, '{"person": "%s"}' % self.fullURItoAbsoluteURI(person2_uri), content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(customer_uri)
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

        response = self.c.put(listfieldtest_uri, '{"intlist": [1, 2, 4], "stringlist": ["a", "b", "c", "d"]}', content_type='application/json')
        self.assertEqual(response.status_code, 204)

        response = self.c.get(listfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['intlist'], [1, 2, 4])
        self.assertEqual(response['stringlist'], ['a', 'b', 'c', 'd'])

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

        response = self.c.patch(customer_uri, '{"person": "%s"}' % self.fullURItoAbsoluteURI(person1_uri), content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(customer_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['person']['name'], 'Person 1 PATCHED')
        self.assertEqual(response['person']['optional'], 'Optional PATCHED')

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

        self.assertFalse('number' in response['dictionary'])
        self.assertEqual(response['dictionary']['a'], 42)

        response = self.c.patch(listfieldtest_uri, '{"intlist": [1, 2, 42]}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(listfieldtest_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['intlist'], [1, 2, 42])
        self.assertEqual(response['stringlist'], ['a', 'b', 'c', 'd'])

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

    def test_embeddedlist(self):
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

        response = self.c.patch(embedded1_uri, '{"name": "Embedded person 1 PATCHED"}', content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.c.get(embedded1_uri)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)

        self.assertEqual(response['name'], 'Embedded person 1 PATCHED')
        self.assertEqual(response['optional'], None)
        self.assertEqual(response['resource_uri'], embedded1_uri)

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

        # TODO: Test patch requests (https://code.djangoproject.com/ticket/17797)
        # TODO: Test delete
