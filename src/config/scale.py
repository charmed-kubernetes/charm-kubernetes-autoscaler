import logging
from errors import JujuConfigError
from config.base import JujuBase

logger = logging.getLogger(__name__)


class JujuScale(JujuBase):
    @staticmethod
    def invalid(min_max_app):
        min_max_app = min_max_app.split(":")
        if len(min_max_app) != 3:
            return f"Must contain 3 parts <min>:<max>:<application> -- {min_max_app}"
        _min, _max, app = min_max_app
        try:
            _min, _max = int(_min), int(_max)
        except ValueError:
            _min, _max = -1, -1
        if _min < 0 or _max < 0:
            return f"<min> and <max> must be non-integers -- {min_max_app[:2]}"
        if _max <= _min:
            return f"<min> must be less than <max> -- {min_max_app[:2]}"

    def __init__(self, cfg):
        super().__init__(cfg)
        self.scale = []
        if cfg.strip() != "":
            self.scale = [parts.strip() for parts in cfg.split(",")]
            failures = [fails for fails in map(self.invalid, self.scale) if fails]
            if failures:
                logger.error("invalid juju_scale configuration: %s", ", ".join(failures))
                raise JujuConfigError("juju_scale invalid")
