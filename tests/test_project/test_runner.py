from django.test import simple

class TPMETestSuiteRunner(simple.DjangoTestSuiteRunner):
    """
    It is the same as in DjangoTestSuiteRunner, but without databases.
    """

    def setup_databases(self, **kwargs):
        pass

    def teardown_databases(self, old_config, **kwargs):
        pass
