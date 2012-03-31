from django.test.simple import DjangoTestSuiteRunner

class TPMETestSuiteRunner(DjangoTestSuiteRunner):
    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """
        Run the unit tests for all the test labels in the provided list.
        Labels must be of the form:
         - app.TestClass.test_method
            Run a single specific test method
         - app.TestClass
            Run all the test methods in a given class
         - app
            Search for doctests and unittests in the named application.

        When looking for tests, the test runner will look in the models and
        tests modules for the application.

        A list of 'extra' tests may also be provided; these tests
        will be added to the test suite.

        Returns the number of tests that failed.
        """
        
        self.setup_test_environment()
        suite = self.build_suite(test_labels, extra_tests)
        #old_config = self.setup_databases()
        result = self.run_suite(suite)
        #self.teardown_databases(old_config)
        self.teardown_test_environment()
        return self.suite_result(suite, result)