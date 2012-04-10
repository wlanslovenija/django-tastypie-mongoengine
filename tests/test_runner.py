from django.test import simple

class TPMETestSuiteRunner(simple.DjangoTestSuiteRunner):
    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """
        It is the same as in DjangoTestSuiteRunner, but without databases.
        """
        
        self.setup_test_environment()
        suite = self.build_suite(test_labels, extra_tests)
        result = self.run_suite(suite)
        self.teardown_test_environment()
        return self.suite_result(suite, result)