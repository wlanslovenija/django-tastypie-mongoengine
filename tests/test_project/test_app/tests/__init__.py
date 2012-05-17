from __future__ import absolute_import

from django.utils import unittest

from . import test_basic

# We patch Django test client with support for PATCH request
from . import django_patch

def suite():
    return unittest.TestSuite((
        unittest.TestLoader().loadTestsFromTestCase(test_basic.BasicTest),
    ))
