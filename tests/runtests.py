#!/usr/bin/env python
import os, sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def runtests():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

    from django.core.management import execute_from_command_line

    argv = [sys.argv[0], 'test']
    execute_from_command_line(argv)
    sys.exit(0)

if __name__ == "__main__":
    runtests()
