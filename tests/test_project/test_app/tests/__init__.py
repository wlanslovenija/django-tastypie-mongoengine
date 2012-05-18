from __future__ import absolute_import

from django.utils import unittest

from . import test_basic

def suite():
    return unittest.TestSuite((
        unittest.TestLoader().loadTestsFromTestCase(test_basic.BasicTest),
    ))
