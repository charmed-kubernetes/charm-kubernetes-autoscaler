import binascii
import logging
import base64
from errors import JujuConfigError
from config.base import JujuBase

logger = logging.getLogger(__name__)


class JujuCaCert(JujuBase):
    def __init__(self, cfg):
        super().__init__(cfg)
        try:
            base64.b64decode(cfg)
        except binascii.Error as err:
            logger.exception("invalid juju_ca_cert configuration: %s", err)
            raise JujuConfigError("juju_ca_cert invalid") from err
