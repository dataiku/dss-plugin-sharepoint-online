import logging
import time


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')


class RobustSessionError(ValueError):
    pass


class RobustSession():
    def __init__(self, session=None, status_codes_to_retry=None, max_retries=1, base_retry_timer_sec=60):
        logger.info("Init RobustSession")
        self.session = session
        self.status_codes_to_retry = status_codes_to_retry or []
        self.max_retries = max_retries
        self.base_retry_timer_sec = base_retry_timer_sec

    def update_settings(self, session=None, status_codes_to_retry=None, max_retries=None, base_retry_timer_sec=None):
        self.session = session or self.session
        self.status_codes_to_retry = status_codes_to_retry or self.status_codes_to_retry
        self.max_retries = max_retries or self.max_retries
        self.base_retry_timer_sec = base_retry_timer_sec or self.base_retry_timer_sec

    def connect(self, connection_function=None):
        self.connection_function = connection_function or self.connection_function
        if self.connection_function:
            self.session = self.retry(self.connection_function)

    def get(self, url, dku_rs_off=False, **kwargs):
        if dku_rs_off:
            return self.session.get(url, **kwargs)
        else:
            return self.retry(self.session.get(url, **kwargs))

    def post(self, url, dku_rs_off=False, **kwargs):
        if dku_rs_off:
            return self.session.post(url, **kwargs)
        else:
            return self.retry(self.session.post(url, **kwargs))

    def retry(self, func):
        attempt_number = 0
        successful_func = False
        while not successful_func and attempt_number <= self.max_retries:
            try:
                attempt_number += 1
                logger.info("RobustSession:retry:attempt #{}".format(attempt_number))
                response = func
                if hasattr(response, 'status_code'):
                    if response.status_code < 400:
                        successful_func = True
                    elif response.status_code in self.status_codes_to_retry:
                        logger.warning("Error {} on attempt #{}".format(response.status_code, attempt_number))
                        self.session.close()
                        self.sleep(self.base_retry_timer_sec * attempt_number)
                        self.connect()
                else:
                    # Probably a connection function from 3rd party lib
                    # So if no exception, we're all set
                    successful_func = True
            except Exception as err:
                logger.warning("ERROR:{}".format(err))
                logger.warning("on attempt #{}".format(attempt_number))
                if attempt_number == self.max_retries:
                    raise RobustSessionError("Error on attempt #{}: {}".format(attempt_number, err))
                self.session.close()
                self.sleep(self.base_retry_timer_sec * attempt_number)
                self.connect()
        return response

    def sleep(self, time_to_sleep_in_sec):
        logger.info("Sleeping {} seconds".format(time_to_sleep_in_sec))
        time.sleep(time_to_sleep_in_sec)
