from safe_logger import SafeLogger
from dss_constants import DSSConstants
import time

logger = SafeLogger("sharepoint-online plugin FreshToken", DSSConstants.SECRET_PARAMETERS_KEYS)
TOKEN_VALIDITY_SAFETY_MARGIN_SECONDS = 60


class FreshToken():
    def __init__(self, token_refresh_method=None, access_token=None):
        logger.info("FreshToken init")
        if access_token:
            logger.info("Permanent access token provided")
            self.current_token = access_token
            self.token_refresh_method = self._default_refresh_method
            self.token_renewal_time = None
        if token_refresh_method is not None:
            logger.info("Using refresh method")
            self.token_refresh_method = token_refresh_method
            self.refresh_token()

    def _default_refresh_method(self):
        return self.current_token

    def token_needs_renewal(self):
        if self.token_renewal_time is None:
            return True
        epoch_time_now = int(time.time())
        return self.token_renewal_time <= epoch_time_now

    def refresh_token(self):
        self.current_token = self.token_refresh_method()
        decoded_jwt = decode_jwt(self.current_token)
        self.token_renewal_time = decoded_jwt.get("exp", None)
        if isinstance(self.token_renewal_time, int):
            self.token_renewal_time = self.token_renewal_time - TOKEN_VALIDITY_SAFETY_MARGIN_SECONDS
        logger.info("The token is valid until {}".format(self.token_renewal_time))

    @property
    def access_token(self):
        if not self.token_needs_renewal():
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
        token_payload = sub_tokens[1]
        padded_token = token_payload + "=" * (-len(token_payload) % 4)
        decoded_token = base64.urlsafe_b64decode(padded_token.encode('utf-8'))
        json_token = json.loads(decoded_token)
        return json_token
    except Exception as error:
        logger.error("Could not decode JWT token ({})".format(error))
    return {}
