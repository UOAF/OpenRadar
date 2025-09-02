"""Logging configuration for OpenRadar application.

Provides configurable logging to stdout and/or file with automatic crash dump functionality.
Default behavior is stdout logging with optional file logging and crash dumps saved to files.
Stdout logging is always enabled unless explicitly disabled via disable_stdout=True.

Features:
- Memory buffering: All logs are kept in memory for crash dump inclusion
- Crash dumps include: System info, traceback, and recent application logs
- Configurable buffer capacity to control memory usage

Usage:
    from logging_config import setup_logging, get_logger
    
    # Setup logging (call once at application start)
    setup_logging()  # Logs to stdout only
    
    # Setup dual logging (stdout + file)
    setup_logging(log_to_file=True)
    
    # Setup file-only logging (no stdout)
    setup_logging(log_to_file=True, disable_stdout=True)
    
    # Get logger for specific module
    logger = get_logger(__name__)
    logger.info("Application started")
    logger.error("Something went wrong")
    
    # Access buffered logs if needed
    from logging_config import get_buffered_logs, save_current_logs_to_file
    recent_logs = get_buffered_logs()
    log_file = save_current_logs_to_file()
"""

import logging
import logging.handlers
import sys
import traceback
import datetime
from pathlib import Path
from typing import Optional


class NonFlushingMemoryHandler(logging.handlers.MemoryHandler):
    """A MemoryHandler that doesn't auto-flush on ERROR level or capacity.
    
    This ensures logs are retained in memory for crash dump purposes
    rather than being flushed to the target handler.
    """
    
    def shouldFlush(self, record):
        """Override to prevent automatic flushing.
        
        The default MemoryHandler flushes when:
        1. Buffer reaches capacity 
        2. Record level >= ERROR
        
        We want to prevent this to keep logs in memory for crash dumps.
        """
        return False  # Never auto-flush
    
    def emit(self, record):
        """Override emit to handle buffer overflow manually."""
        if len(self.buffer) >= self.capacity:
            # Remove oldest record to make room (FIFO)
            self.buffer.pop(0)
        
        # Add the new record
        self.buffer.append(record)

# Default log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Default log directory
DEFAULT_LOG_DIR = Path("logs")

# Global reference to the configured logger
_root_logger: Optional[logging.Logger] = None
_memory_handler: Optional[logging.handlers.MemoryHandler] = None
_log_to_file: bool = False
_log_dir: Path = DEFAULT_LOG_DIR


def setup_logging(level: int = logging.INFO,
                  log_to_file: bool = False,
                  log_dir: Optional[Path] = None,
                  max_file_size_mb: int = 10,
                  backup_count: int = 5,
                  disable_stdout: bool = False,
                  memory_buffer_capacity: int = 10000) -> logging.Logger:
    """Setup logging configuration for the OpenRadar application.
    
    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_to_file: If True, also log to rotating files. Always logs to stdout unless disable_stdout=True.
        log_dir: Directory for log files (only used if log_to_file=True)
        max_file_size_mb: Maximum size of each log file in MB before rotation
        backup_count: Number of backup log files to keep
        disable_stdout: If True, disable stdout logging (only log to files)
        memory_buffer_capacity: Number of log records to keep in memory for crash dumps
        
    Returns:
        The configured root logger
    """
    global _root_logger, _log_to_file, _log_dir, _memory_handler

    _log_to_file = log_to_file
    _log_dir = log_dir or DEFAULT_LOG_DIR

    # Get the root logger
    _root_logger = logging.getLogger()
    _root_logger.setLevel(level)

    # Clear any existing handlers
    _root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Create a dummy target handler for the MemoryHandler (required but not used)
    dummy_handler = logging.NullHandler()

    # Create NonFlushingMemoryHandler to capture logs for crash dumps
    _memory_handler = NonFlushingMemoryHandler(
        capacity=memory_buffer_capacity,
        target=dummy_handler  # Required but we'll handle flushing manually
    )
    _memory_handler.setLevel(logging.DEBUG)  # Capture all levels
    _memory_handler.setFormatter(formatter)
    _root_logger.addHandler(_memory_handler)

    # Always add stdout handler unless explicitly disabled
    if not disable_stdout:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(level)
        stdout_handler.setFormatter(formatter)
        _root_logger.addHandler(stdout_handler)
        print("Logging to stdout")

    # Add file handler if requested
    if log_to_file:
        # Ensure log directory exists
        _log_dir.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        log_file = _log_dir / "openradar.log"
        file_handler = logging.handlers.RotatingFileHandler(log_file,
                                                            maxBytes=max_file_size_mb * 1024 * 1024,
                                                            backupCount=backup_count,
                                                            encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        _root_logger.addHandler(file_handler)

        print(f"Logging to file: {log_file}")

    # Setup crash dump handler
    setup_crash_handler()

    return _root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module/class.
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        A logger instance
    """
    if _root_logger is None:
        # Auto-setup with defaults if not already configured
        setup_logging()

    return logging.getLogger(name)


def setup_crash_handler():
    """Setup automatic crash dump functionality.
    
    This replaces the default sys.excepthook to log unhandled exceptions
    and save them to a crash dump file with all buffered logs.
    """

    def crash_handler(exc_type, exc_value, exc_traceback):
        """Handle unhandled exceptions by logging them and saving crash dump with logs."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow Ctrl+C to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Create crash dump
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_dump_file = _log_dir / f"crash_dump_{timestamp}.log"

        # Ensure crash dump directory exists
        _log_dir.mkdir(parents=True, exist_ok=True)

        # Format crash information (at the top)
        crash_info = [
            f"OpenRadar Crash Dump - {timestamp}",
            "=" * 80,
            f"Exception Type: {exc_type.__name__}",
            f"Exception Value: {exc_value}",
            "",
            "Traceback:",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            "",
            "System Information:",
            f"Python Version: {sys.version}",
            f"Platform: {sys.platform}",
            f"Arguments: {sys.argv}",
            "",
            "=" * 80,
            "APPLICATION LOGS (Most Recent First):",
            "=" * 80,
        ]

        # Get buffered logs from MemoryHandler
        buffered_logs = []
        if _memory_handler is not None and hasattr(_memory_handler, 'buffer'):
            # Get logs from the buffer (most recent first)
            log_records = list(reversed(_memory_handler.buffer))

            for record in log_records:
                try:
                    # Format the log record
                    log_line = _memory_handler.format(record)
                    buffered_logs.append(log_line)
                except Exception as format_error:
                    # Fallback if formatting fails
                    buffered_logs.append(f"[ERROR FORMATTING LOG]: {record.getMessage()}")

        # If no logs in buffer, add a note
        if not buffered_logs:
            buffered_logs.append("[No logs in memory buffer]")

        # Combine crash info and logs
        crash_text = "\n".join(crash_info)
        logs_text = "\n".join(buffered_logs)
        full_crash_dump = crash_text + "\n" + logs_text

        # Save crash dump to file
        try:
            with open(crash_dump_file, 'w', encoding='utf-8') as f:
                f.write(full_crash_dump)
            print(f"Crash dump with logs saved to: {crash_dump_file}")
        except Exception as e:
            print(f"Failed to save crash dump: {e}")

        # Log the crash if logger is available
        if _root_logger is not None:
            _root_logger.critical("Unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))

        # Print to stderr as fallback
        print(f"FATAL ERROR: {exc_type.__name__}: {exc_value}", file=sys.stderr)
        print(f"Crash dump saved to: {crash_dump_file}", file=sys.stderr)

        # Call the original exception handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    # Install our crash handler
    sys.excepthook = crash_handler


def log_system_info():
    """Log basic system information at startup."""
    logger = get_logger("openradar.system")
    logger.info(f"OpenRadar starting - Python {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Arguments: {' '.join(sys.argv)}")


def log_performance_metrics(fps: float, cpu_time_us: float, gpu_time_us: float, radar_sleep: float):
    """Log performance metrics (can be called periodically).
    
    Args:
        fps: Frames per second
        cpu_time_us: CPU frame time in microseconds
        gpu_time_us: GPU frame time in microseconds  
        radar_sleep: Radar processing sleep time
    """
    logger = get_logger("openradar.performance")
    logger.debug(f"FPS: {fps:.1f}, CPU: {cpu_time_us:.0f}μs, GPU: {gpu_time_us:.0f}μs, Sleep: {radar_sleep:.3f}s")


def get_buffered_logs() -> list[str]:
    """Get the current buffered logs from the MemoryHandler.
    
    Returns:
        List of formatted log messages (most recent first)
    """
    buffered_logs = []
    if _memory_handler is not None and hasattr(_memory_handler, 'buffer'):
        # Get logs from the buffer (most recent first)
        log_records = list(reversed(_memory_handler.buffer))

        for record in log_records:
            try:
                # Format the log record
                log_line = _memory_handler.format(record)
                buffered_logs.append(log_line)
            except Exception:
                # Fallback if formatting fails
                buffered_logs.append(f"[ERROR FORMATTING LOG]: {record.getMessage()}")

    return buffered_logs


def clear_memory_buffer():
    """Clear the memory buffer of logged messages."""
    if _memory_handler is not None:
        _memory_handler.buffer.clear()


def save_current_logs_to_file(filename: Optional[str] = None) -> Path:
    """Save current buffered logs to a file.
    
    Args:
        filename: Optional filename. If not provided, uses timestamp.
        
    Returns:
        Path to the saved log file
    """
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs_snapshot_{timestamp}.log"

    log_file = _log_dir / filename
    _log_dir.mkdir(parents=True, exist_ok=True)

    logs = get_buffered_logs()

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"OpenRadar Log Snapshot - {datetime.datetime.now()}\n")
        f.write("=" * 80 + "\n")
        f.write("\n".join(logs))

    return log_file


# Convenience function for quick logging setup
def quick_setup(debug: bool = False, log_to_file: bool = False, memory_buffer_capacity: int = 1000) -> logging.Logger:
    """Quick logging setup with sensible defaults.
    
    Args:
        debug: If True, set level to DEBUG, otherwise INFO
        log_to_file: If True, log to files in addition to stdout
        memory_buffer_capacity: Number of log records to keep in memory for crash dumps
        
    Returns:
        The configured root logger
    """
    level = logging.DEBUG if debug else logging.INFO
    return setup_logging(level=level, log_to_file=log_to_file, memory_buffer_capacity=memory_buffer_capacity)


def setup_dual_logging(level: int = logging.INFO,
                       log_dir: Optional[Path] = None,
                       max_file_size_mb: int = 10,
                       backup_count: int = 5,
                       memory_buffer_capacity: int = 1000) -> logging.Logger:
    """Setup dual logging to both stdout and files with memory buffering.
    
    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_dir: Directory for log files
        max_file_size_mb: Maximum size of each log file in MB before rotation
        backup_count: Number of backup log files to keep
        memory_buffer_capacity: Number of log records to keep in memory for crash dumps
        
    Returns:
        The configured root logger
    """
    return setup_logging(level=level,
                         log_to_file=True,
                         log_dir=log_dir,
                         max_file_size_mb=max_file_size_mb,
                         backup_count=backup_count,
                         disable_stdout=False,
                         memory_buffer_capacity=memory_buffer_capacity)
