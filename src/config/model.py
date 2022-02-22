import logging
import uuid
from errors import JujuConfigError
from config.base import JujuBase

logger = logging.getLogger(__name__)


class JujuModel(JujuBase):
    def __init__(self, cfg):
        super().__init__(cfg)
        if cfg.strip() != "":
            try:
                uuid.UUID(cfg)
            except ValueError as err:
                logger.exception("invalid juju_default_model_uuid configuration: %s", err)
                raise JujuConfigError("juju_default_model_uuid invalid") from err
