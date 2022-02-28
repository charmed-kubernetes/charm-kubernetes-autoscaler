from functools import partial
from config.scale import ConfigScale
from config.controller import ConfigController
from config.ca_cert import ConfigCaCert
from config.uuid import ConfigUUID
from config.key_value import KeyValue


class ConfigParser:
    _types = {}

    def __init__(self, prefix):
        self._prefix = prefix
        self._cached = {}

    def keys(self):
        return self._types.keys()

    def __getitem__(self, item):
        try:
            value = self._cached[item]
        except KeyError:
            cast, _default = self._types[item]
            value = cast(self._storage[item])
            self._cached[item] = value
        return value

    def load(self, charm):
        for opt in self._types.keys():
            charm_cfg = charm.config.get(f"{self._prefix}{opt}")
            stored_cfg = self[opt]
            if charm_cfg != stored_cfg:
                self._apply(opt, charm_cfg)

    def _apply(self, item, value):
        cast, as_default = self._types[item]
        as_default = type(as_default)
        if isinstance(value, as_default):
            self._cached[item] = cast(value)
            self._storage[item] = value
        else:
            raise TypeError(f"value {value} must be of type {as_default}")

        return value


class AutoscalerConfig(ConfigParser):
    _types = {"extra_args": (partial(KeyValue, "autoscaler_extra_args"), "{}")}

    @property
    def _storage(self):
        return self._stored.autoscaler_config

    def __init__(self, storage):
        super(AutoscalerConfig, self).__init__("autoscaler_")
        self._stored = storage
        self._stored.set_default(
            autoscaler_config={key: default for key, (cast, default) in self._types.items()}
        )


class JujuConfig(ConfigParser):
    _types = {
        "api_endpoints": (ConfigController, ""),
        "ca_cert": (ConfigCaCert, ""),
        "username": (str, ""),
        "password": (str, ""),
        "default_model_uuid": (partial(ConfigUUID, "juju_default_model_uuid"), ""),
        "scale": (ConfigScale, ""),
    }

    @property
    def _storage(self):
        return self._stored.juju_config

    def __init__(self, storage):
        super(JujuConfig, self).__init__("juju_")
        self._stored = storage
        self._stored.set_default(
            juju_config={key: default for key, (cast, default) in self._types.items()}
        )


__all__ = ["JujuConfig", "AutoscalerConfig"]
