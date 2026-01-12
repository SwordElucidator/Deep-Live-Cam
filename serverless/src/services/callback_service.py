"""
Callback Service

Webhook callback handling with retry logic.
"""

import time
from typing import Dict, Any

import requests

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CallbackError(Exception):
    """Callback operation error"""
    pass


class CallbackService:
    """
    Webhook callback service.
    
    Sends completion/error callbacks with retry logic.
    """
    
    @staticmethod
    def send(
        url: str,
        payload: Dict[str, Any],
        max_retries: int = None,
        timeout: int = None
    ) -> bool:
        """
        Send webhook callback.
        
        Args:
            url: Webhook URL
            payload: JSON payload to send
            max_retries: Maximum retry attempts (default from settings)
            timeout: Request timeout in seconds (default from settings)
            
        Returns:
            True if successful
            
        Raises:
            CallbackError: If callback fails after all retries
        """
        if max_retries is None:
            max_retries = settings.callback_max_retries
        if timeout is None:
            timeout = settings.callback_timeout
        
        logger.info(f"Sending callback to {url}")
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=timeout,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Deep-Live-Cam-API/1.0'
                    }
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Callback sent successfully (status: {response.status_code})")
                    return True
                else:
                    last_error = CallbackError(
                        f"Callback returned status {response.status_code}: {response.text}"
                    )
                    logger.warning(
                        f"Callback attempt {attempt + 1}/{max_retries} "
                        f"failed with status {response.status_code}"
                    )
                    
            except requests.Timeout:
                last_error = CallbackError(f"Callback timed out after {timeout}s")
                logger.warning(f"Callback attempt {attempt + 1}/{max_retries} timed out")
                
            except requests.RequestException as e:
                last_error = CallbackError(f"Callback request failed: {str(e)}")
                logger.warning(f"Callback attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                
            except Exception as e:
                last_error = CallbackError(f"Unexpected error: {str(e)}")
                logger.warning(f"Callback attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            
            # Exponential backoff (5s, 15s, 45s)
            if attempt < max_retries - 1:
                sleep_time = 5 * (3 ** attempt)
                logger.info(f"Retrying callback in {sleep_time}s...")
                time.sleep(sleep_time)
        
        logger.error(f"Callback failed after {max_retries} attempts: {last_error}")
        raise last_error
