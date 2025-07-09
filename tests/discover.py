import sys
from unittest import TextTestRunner, defaultTestLoader


def run(*, exit=True):
    test_suite = defaultTestLoader.discover("tests")
    result = TextTestRunner(verbosity=2).run(test_suite)
    success = result.wasSuccessful()

    if exit:
        sys.exit(not success)

    return success
