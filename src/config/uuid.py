import logging
import uuid
from errors import JujuConfigError
from config.base import JujuBase

logger = logging.getLogger(__name__)


class JujuUUID(JujuBase):
    def __init__(self, option, cfg):
        super().__init__(cfg)
        if cfg.strip() != "":
            try:
                uuid.UUID(cfg)
            except ValueError as err:
                logger.exception("invalid %s configuration: %s", option, err)
                raise JujuConfigError(f"{option} invalid") from err
