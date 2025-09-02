import sys
import argparse
import os
import logging
from pathlib import Path

from logging_config import setup_logging, get_logger, log_system_info
import config
from app import App


def main():
    # Parse arguments first to check for debug flag
    parser = argparse.ArgumentParser(prog='OpenRadar', description='TacView realtime telemetry radar tool')
    test_ini_path = os.path.join(os.getcwd(), 'Data', 'test.ini')
    parser.add_argument('-i', '--ini', nargs='?', const=test_ini_path, default=None, help='Load a test ini file.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--log-file', action='store_true', help='Log to file instead of stdout')

    args = parser.parse_args()

    # Setup logging based on configuration with command line overrides
    log_level_str = config.app_config.get_str("logging", "level")
    try:
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    except AttributeError:
        log_level = logging.INFO

    # Override log level if debug flag is set
    if args.debug:
        log_level = logging.DEBUG

    log_to_file = config.app_config.get_bool("logging", "log_to_file")
    # Override log destination if log-file flag is set
    if args.log_file:
        log_to_file = True

    disable_stdout = config.app_config.get_bool("logging", "disable_stdout")
    log_dir_str = config.app_config.get_str("logging", "log_directory")
    max_file_size = config.app_config.get_int("logging", "max_file_size_mb")
    backup_count = config.app_config.get_int("logging", "backup_count")
    memory_buffer_capacity = config.app_config.get_int("logging", "memory_buffer_capacity")

    # Setup logging
    log_dir = Path(log_dir_str) if log_dir_str else None
    setup_logging(level=log_level,
                  log_to_file=log_to_file,
                  log_dir=log_dir,
                  max_file_size_mb=max_file_size,
                  backup_count=backup_count,
                  disable_stdout=disable_stdout,
                  memory_buffer_capacity=memory_buffer_capacity)

    # Set logger for config, Done here to avoid chicken or egg problem
    config.app_config.set_logger(get_logger("config"))

    # Log system information
    log_system_info()
    config.app_config.log_config_dirs()

    # Get logger for this module
    logger = get_logger(__name__)
    logger.info("OpenRadar application starting")

    try:
        theApp = App(sys.argv)

        logger.info(f"Starting application with args: {args}")
        theApp.on_execute(args)

    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
        raise
    finally:
        logger.info("OpenRadar application shutting down")


if __name__ == '__main__':
    main()
