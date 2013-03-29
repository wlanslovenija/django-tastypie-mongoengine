import os

from django.utils import unittest

def suite():
    return unittest.TestSuite((
        unittest.TestLoader().discover(
            start_dir=os.path.abspath(os.path.dirname(__file__)),
            top_level_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')),
        ),
    ))
