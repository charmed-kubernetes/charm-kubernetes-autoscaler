from config.scale import JujuScale
from config.controller import JujuController
from config.ca_cert import JujuCaCert
from config.model import JujuModel


class JujuConfig:
    _types = {
        "api_endpoints": (JujuController, ""),
        "ca_cert": (JujuCaCert, ""),
        "username": (str, ""),
        "password": (str, ""),
        "default_model_uuid": (JujuModel, ""),
        "scale": (JujuScale, ""),
    }

    def __init__(self, storage):
        self._stored = storage
        self._stored.set_default(
            juju_config={key: default for key, (cast, default) in self._types.items()}
        )
        self._cached = {}

    def load(self, charm):
        for opt in self._types.keys():
            charm_cfg = charm.config.get(f"juju_{opt}")
            stored_cfg = self[opt]
            if charm_cfg != stored_cfg:
                self._apply(opt, charm_cfg)

    def __getitem__(self, item):
        try:
            value = self._cached[item]
        except KeyError:
            cast, _default = self._types[item]
            value = cast(self._stored.juju_config[item])
            self._cached[item] = value
        return value

    def _apply(self, item, value):
        cast, as_default = self._types[item]
        as_default = type(as_default)
        if isinstance(value, as_default):
            self._cached[item] = cast(value)
            self._stored.juju_config[item] = value
        else:
            raise TypeError(f"value {value} must be of type {as_default}")

        return value


__all__ = ["JujuConfig"]
