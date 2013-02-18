import urlparse

from django.conf import settings
from django.test import client, simple, testcases
from django.utils import unittest

from mongoengine import connect, connection
from mongoengine.django import tests

class MongoEngineTestSuiteRunner(simple.DjangoTestSuiteRunner):
    """
    It is the same as in DjangoTestSuiteRunner, but without relational databases.

    It also supports filtering only wanted tests through ``TEST_RUNNER_FILTER``
    Django setting.
    """

    db_name = 'test_%s' % settings.MONGO_DATABASE_NAME

    def _filter_suite(self, suite):
        filters = getattr(settings, 'TEST_RUNNER_FILTER', None)

        if filters is None:
            # We do NOT filter if filters are not set
            return suite

        filtered = unittest.TestSuite()

        for test in suite:
            if isinstance(test, unittest.TestSuite):
                filtered.addTests(self._filter_suite(test))
            else:
                for f in filters:
                    if test.id().startswith(f):
                        filtered.addTest(test)

        return filtered

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = super(MongoEngineTestSuiteRunner, self).build_suite(test_labels, extra_tests=None, **kwargs)
        suite = self._filter_suite(suite)
        return simple.reorder_suite(suite, (testcases.TestCase,))

    def setup_databases(self, **kwargs):
        connection.disconnect()
        connect(self.db_name, **getattr(settings, 'MONGO_DATABASE_OPTIONS', {}))

    def teardown_databases(self, old_config, **kwargs):
        connection.get_connection().drop_database(self.db_name)

class MongoEngineTestCase(tests.MongoTestCase):
    """
    A bugfixed version, see this `pull request`_.
    
    .. _pull request: https://github.com/hmarr/mongoengine/pull/506
    """

    def __init__(self, methodName='runtest'):
        # We skip MongoTestCase init
        super(tests.MongoTestCase, self).__init__(methodName)

    def _post_teardown(self):
        self.db = connection.get_db()
        super(MongoEngineTestCase, self)._post_teardown()

# We also patch Django so that it supports PATCH requests (used by Tastypie)
# Taken from https://code.djangoproject.com/attachment/ticket/17797/django-test-client-PATCH.patch

def requestfactory_patch(self, path, data={}, content_type=client.MULTIPART_CONTENT, **extra):
    """
    Construct a PATCH request.
    """
    
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
