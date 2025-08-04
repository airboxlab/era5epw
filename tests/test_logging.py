import logging
import unittest
from io import StringIO

from era5epw.logcfg import init_logging


class TestLoggingConfiguration(unittest.TestCase):
    """Test the logging configuration with verbose and non-verbose modes."""

    def setUp(self):
        """Set up test fixtures."""
        self.log_capture_string = StringIO()
        self.handler = logging.StreamHandler(self.log_capture_string)
        self.handler.setLevel(logging.DEBUG)

    def test_non_verbose_mode_suppresses_info_and_warning_logs(self):
        """Test that non-verbose mode suppresses INFO and WARNING logs from CDS client, only
        showing ERROR logs."""
        # Initialize logging in non-verbose mode
        init_logging(verbose=False)

        # Get the CDS client loggers
        cdsapi_logger = logging.getLogger("cdsapi")
        legacy_logger = logging.getLogger("ecmwf.datastores.legacy_client")

        # Add our capture handler to the loggers
        cdsapi_logger.addHandler(self.handler)
        legacy_logger.addHandler(self.handler)

        # Test that INFO messages are not logged
        cdsapi_logger.info("Test INFO message from cdsapi")
        legacy_logger.info("Test INFO message from legacy client")

        # Test that WARNING messages are not logged (new behavior)
        cdsapi_logger.warning("Test WARNING message from cdsapi")
        legacy_logger.warning("Test WARNING message from legacy client")

        # Test that ERROR messages are logged
        cdsapi_logger.error("Test ERROR message from cdsapi")
        legacy_logger.error("Test ERROR message from legacy client")

        log_contents = self.log_capture_string.getvalue()

        # INFO and WARNING messages should not appear
        self.assertNotIn("Test INFO message from cdsapi", log_contents)
        self.assertNotIn("Test INFO message from legacy client", log_contents)
        self.assertNotIn("Test WARNING message from cdsapi", log_contents)
        self.assertNotIn("Test WARNING message from legacy client", log_contents)

        # ERROR messages should appear
        self.assertIn("Test ERROR message from cdsapi", log_contents)
        self.assertIn("Test ERROR message from legacy client", log_contents)

    def test_verbose_mode_shows_info_logs(self):
        """Test that verbose mode shows INFO logs from CDS client."""
        # Initialize logging in verbose mode
        init_logging(verbose=True)

        # Get the CDS client loggers
        cdsapi_logger = logging.getLogger("cdsapi")
        legacy_logger = logging.getLogger("ecmwf.datastores.legacy_client")

        # Add our capture handler to the loggers
        cdsapi_logger.addHandler(self.handler)
        legacy_logger.addHandler(self.handler)

        # Test that INFO messages are logged
        cdsapi_logger.info("Test INFO message from cdsapi")
        legacy_logger.info("Test INFO message from legacy client")

        # Test that WARNING messages are also logged
        cdsapi_logger.warning("Test WARNING message from cdsapi")
        legacy_logger.warning("Test WARNING message from legacy client")

        log_contents = self.log_capture_string.getvalue()

        # Both INFO and WARNING messages should appear
        self.assertIn("Test INFO message from cdsapi", log_contents)
        self.assertIn("Test INFO message from legacy client", log_contents)
        self.assertIn("Test WARNING message from cdsapi", log_contents)
        self.assertIn("Test WARNING message from legacy client", log_contents)

    def test_logger_levels_are_set_correctly(self):
        """Test that logger levels are set correctly based on verbose flag."""
        # Test non-verbose mode - should be ERROR level
        init_logging(verbose=False)
        cdsapi_logger = logging.getLogger("cdsapi")
        legacy_logger = logging.getLogger("ecmwf.datastores.legacy_client")

        self.assertEqual(cdsapi_logger.level, logging.ERROR)
        self.assertEqual(legacy_logger.level, logging.ERROR)

        # Test verbose mode - should be INFO level
        init_logging(verbose=True)

        self.assertEqual(cdsapi_logger.level, logging.INFO)
        self.assertEqual(legacy_logger.level, logging.INFO)

    def tearDown(self):
        """Clean up after tests."""
        self.handler.close()


if __name__ == "__main__":
    unittest.main()
