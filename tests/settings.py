# Django settings for tpme_tests project
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

DEBUG = True

# Make this unique, and don't share it with anybody
SECRET_KEY = 'sq=uf!nqw=aibl+y1&5pp=)b7pc=c$4hnh$om*_c48r)^t!ob)'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'tests.urls'

AUTHENTICATION_BACKENDS = (
    'mongoengine.django.auth.MongoEngineBackend',
)

SESSION_ENGINE = 'mongoengine.django.sessions'

TEST_RUNNER = 'tests.test_runner.TPMETestSuiteRunner'

INSTALLED_APPS = (
    'tastypie',
    'tastypie_mongoengine',
    'test_app',
)

import mongoengine
mongoengine.connect('tpme_tests')
