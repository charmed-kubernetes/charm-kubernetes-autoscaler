import logging
from errors import JujuConfigError

logger = logging.getLogger(__name__)


class JujuScale:
    @staticmethod
    def invalid(min_max_app):
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

    @classmethod
    def parse(cls, cfg):
        if cfg.strip() == "":
            return cls([], cfg)
        parts = [parts.strip().split(":") for parts in cfg.split(",")]
        failures = [fails for fails in map(cls.invalid, parts) if fails]
        if failures:
            logger.error("invalid juju_scale configuration: %s", ", ".join(failures))
            return JujuConfigError("juju_scale invalid")
        return cls(parts, cfg)

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.cfg
        elif isinstance(other, JujuScale):
            return other.cfg == self.cfg
        return False

    def __init__(self, scale_params, cfg):
        self.scale = scale_params
        self.cfg = cfg
