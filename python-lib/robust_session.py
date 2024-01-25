import time
import copy
from safe_logger import SafeLogger
from dss_constants import DSSConstants
from common import update_dict_in_kwargs


logger = SafeLogger("sharepoint-online plugin", DSSConstants.SECRET_PARAMETERS_KEYS)


class RobustSessionError(ValueError):
    pass


class RobustSession():
    """
    Implements a retry on status code 429 and connections reset by peer, and a connection reset + retry on error 403
    """
    def __init__(self, session=None, status_codes_to_retry=None, max_retries=1, base_retry_timer_sec=60, attempt_session_reset_on_403=False):
        logger.info("Init RobustSession")
        self.session = session
        self.status_codes_to_retry = status_codes_to_retry or []
        self.max_retries = max_retries
        self.base_retry_timer_sec = base_retry_timer_sec
        self.connection_args = []
        self.connection_kwargs = {}
        self.connection_library = None
        self.attempt_session_reset_on_403 = attempt_session_reset_on_403
        self.default_headers = {}

    def update_settings(self, session=None, status_codes_to_retry=None, max_retries=None, base_retry_timer_sec=None, default_headers=None):
        self.session = session or self.session
        self.status_codes_to_retry = status_codes_to_retry or self.status_codes_to_retry
        self.max_retries = max_retries or self.max_retries
        self.base_retry_timer_sec = base_retry_timer_sec or self.base_retry_timer_sec
        self.default_headers = default_headers or self.default_headers

    def connect(self, connection_library=None, *args, **kwargs):
        self.connection_library = connection_library or self.connection_library
        self.connection_args = args or self.connection_args
        self.connection_kwargs = kwargs or self.connection_kwargs
        if self.connection_library:
            self.session = self.retry(self.connection_library.connect, *self.connection_args, **self.connection_kwargs)

    def get(self, url, dku_rs_off=False, **kwargs):
        if dku_rs_off:
            return self.session.get(url, **kwargs)
        else:
            kwargs["url"] = url
            response = self.request_with_403_retry("get", **kwargs)
            return response

    def post(self, url, dku_rs_off=False, **kwargs):
        kwargs = update_dict_in_kwargs(kwargs, "headers", self.default_headers)
        if dku_rs_off:
            response = self.session.post(url, **kwargs)
            return response
        else:
            kwargs["url"] = url
            response = self.request_with_403_retry("post", **kwargs)
            return response

    def request_with_403_retry(self, verb, **kwargs):
        """
        403 error code may be result of throttling, rendering the current sessions useless.
        Therefore we try reset the session max_retries times before giving up.
        """
        attempt_number = 0
        attempt_number_on_403 = 0
        successful_request = False
        while (not successful_request) and (attempt_number <= self.max_retries):
            attempt_number += 1
            if verb == "get":
                response = self.retry(self.session.get, **kwargs)
            else:
                response = self.retry(self.session.post, **kwargs)
            if response.status_code == 403 and self.attempt_session_reset_on_403:
                if attempt_number_on_403 >= 1:
                    logger.error("Max number of 403 errors reached. Stopping the plugin to avoid the account to be locked out.")
                    break
                logger.warning("Status code 403. Could be rate limiting, attempting reconnection ({})".format(attempt_number))
                self.safe_session_close()
                self.sleep(30)
                self.connect()
                attempt_number_on_403 += 1
            else:
                attempt_number_on_403 = 0
                successful_request = True
        return response

    def retry(self, func, *args,  **kwargs):
        attempt_number = 0
        successful_func = False
        while (not successful_func) and (attempt_number <= self.max_retries):
            try:
                attempt_number += 1
                logger.info("RobustSession:retry:attempt {} #{}".format(func, attempt_number))
                response = func(*args, **kwargs)
                logger.info("RobustSession:retry:Response={}".format(response))
                if hasattr(response, 'status_code'):
                    if response.status_code < 400:
                        successful_func = True
                    elif response.status_code in self.status_codes_to_retry:
                        logger.warning("Error {} on attempt #{}".format(response.status_code, attempt_number))
                        self.sleep(self.base_retry_timer_sec * attempt_number)
                    else:
                        return response
                else:
                    # Probably a connection function from 3rd party lib
                    # So if no exception, we're all set
                    successful_func = True
            except Exception as err:
                logger.warning("ERROR:{}".format(err))
                logger.warning("on attempt #{}".format(attempt_number))
                if attempt_number == self.max_retries:
                    raise RobustSessionError("Error on attempt #{}: {}".format(attempt_number, err))
                self.sleep(self.base_retry_timer_sec * attempt_number)
        return response

    def safe_session_close(self):
        logger.warning("Safely closing session")
        try:
            self.session.close()
        except Exception as err:
            logger.warning("Error while closing session: {}".format(err))

    def sleep(self, time_to_sleep_in_sec):
        logger.info("Sleeping {} seconds".format(time_to_sleep_in_sec))
        time.sleep(time_to_sleep_in_sec)
