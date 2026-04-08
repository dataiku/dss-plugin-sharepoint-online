from safe_logger import SafeLogger
from dss_constants import DSSConstants
import time

logger = SafeLogger("sharepoint-online plugin FreshToken", DSSConstants.SECRET_PARAMETERS_KEYS)
TOKEN_VALIDITY_SAFETY_MARGIN_SECONDS = 60


class FreshToken():
    def __init__(self, token_refresh_method):
        logger.info("FreshToken init")
        if isinstance(token_refresh_method, str):
            logger.info("No refresh method available")
            self.current_token = token_refresh_method
            self.token_refresh_method = self._default_refresh_method
            self.token_validity = None
        else:
            logger.info("Using refresh method")
            self.token_refresh_method = token_refresh_method
            self.refresh_token()

    def _default_refresh_method(self):
        return self.current_token

    def is_token_still_valid(self):
        if self.token_validity is None:
            return True
        epoch_time_now = int(time.time())
        if (epoch_time_now > self.token_validity):
            return False
        return True

    def refresh_token(self):
        self.current_token = self.token_refresh_method()
        decoded_jwt = decode_jwt(self.current_token)
        self.token_validity = decoded_jwt.get("exp", None)
        if isinstance(self.token_validity, int):
            self.token_validity = self.token_validity - TOKEN_VALIDITY_SAFETY_MARGIN_SECONDS
        logger.info("The token is valid until {}".format(self.token_validity))

    @property
    def access_token(self):
        if not self.is_token_still_valid():
            logger.info("Token reaching its time limit, refreshing it...")
            self.refresh_token()
        return self.current_token


def decode_jwt(jwt_token):
    try:
        import base64
        import json
        sub_tokens = jwt_token.split('.')
        if len(sub_tokens) < 2:
            logger.error("JWT format is wrong")
            return {}
        token_of_interest = sub_tokens[1]
        padded_token = token_of_interest + "="*divmod(len(token_of_interest), 4)[1]
        decoded_token = base64.urlsafe_b64decode(padded_token.encode('utf-8'))
        json_token = json.loads(decoded_token)
        return json_token
    except Exception as error:
        logger.error("Could not decode JWT token ({})".format(error))
    return {}
