import pytest

from config.key_value import KeyValue
from errors import ConfigError


def test_default_key_value():
    assert KeyValue("test", "{}").key_values == {}
    assert KeyValue("test", "").key_values == {}


def test_key_not_a_string():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "{1: 'abc'}")
    assert str(ie.value) == "test invalid: Expected key to be a str -- 1 (int)"


def test_val_not_a_string():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "{abc: [1,2,3]}")
    assert str(ie.value) == "test invalid: Expected val to be a str -- [1, 2, 3] (list)"


def test_list_not_key_values():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "[]")
    assert str(ie.value) == "test invalid: yaml or json format - expected a mapping"


def test_error_invalid_yaml():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "{...")
    assert str(ie.value) == "test invalid: not yaml or json format"
