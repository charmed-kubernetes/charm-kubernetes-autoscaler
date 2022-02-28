import logging
import uuid
from errors import ConfigError
from config.base import ConfigBase

logger = logging.getLogger(__name__)


class ConfigUUID(ConfigBase):
    def __init__(self, option, cfg):
        super().__init__(cfg)
        if cfg.strip() != "":
            try:
                uuid.UUID(cfg)
            except ValueError as err:
                logger.exception("invalid %s configuration: %s", option, err)
                raise ConfigError(f"{option} invalid") from err
