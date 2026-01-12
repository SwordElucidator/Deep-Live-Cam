"""
Logger Configuration

Structured JSON logging for the API service.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

from src.config import settings

# Context variable for job ID
current_job_id: ContextVar[Optional[str]] = ContextVar('current_job_id', default=None)


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add job_id from context if available
        job_id = current_job_id.get()
        if job_id:
            log_entry["job_id"] = job_id
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class StandardFormatter(logging.Formatter):
    """Standard log formatter for local development"""
    
    def format(self, record: logging.LogRecord) -> str:
        job_id = current_job_id.get()
        job_prefix = f"[{job_id}] " if job_id else ""
        
        return f"{datetime.utcnow().isoformat()}Z | {record.levelname:8} | {record.name} | {job_prefix}{record.getMessage()}"


def setup_logging(use_json: bool = True) -> None:
    """
    Configure logging for the application
    
    Args:
        use_json: Use JSON formatter (True for production)
    """
    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create formatter
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = StandardFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("insightface").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_job_context(job_id: str) -> None:
    """
    Set the current job ID for log context
    
    Args:
        job_id: Job identifier
    """
    current_job_id.set(job_id)


def clear_job_context() -> None:
    """Clear the current job context"""
    current_job_id.set(None)


class JobLogContext:
    """Context manager for job logging"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.token = None
    
    def __enter__(self):
        self.token = current_job_id.set(self.job_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        current_job_id.set(None)
        return False


# Initialize logging on module import
setup_logging(use_json=True)
