import pytest

from config.key_value import KeyValue
from errors import ConfigError


def test_default_key_value():
    assert KeyValue("test", "{}").key_values == []
    assert KeyValue("test", "").key_values == []


@pytest.mark.parametrize("val", [1, True, "one"])
def test_valid_key_values(val):
    assert KeyValue("test", f"{{key: {val}}}").key_values == [("key", val)]


@pytest.mark.parametrize(
    "val",
    [
        [1, 2],
        [True, False],
        ["one", "two"],
    ],
)
def test_valid_key_value_list(val):
    assert KeyValue("test", f"{{key: {val}}}").key_values == [("key", item) for item in val]


def test_key_not_a_string():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "{1: 'abc'}")
    assert str(ie.value) == "test invalid: Expected key to be a str -- 1 (int)"


def test_val_non_pod_type():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "{abc: {def: {foo: bar}}}")
    assert (
        str(ie.value) == "test invalid: Unexpected type for val -- {'def': {'foo': 'bar'}} (dict)"
    )


def test_val_non_pod_type_list_item():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "{abc: [{def: {foo: bar}}]}")
    assert (
        str(ie.value)
        == "test invalid: Unexpected type for item in val list -- {'def': {'foo': 'bar'}} (dict)"
    )


def test_list_not_key_values():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "[]")
    assert str(ie.value) == "test invalid: yaml or json format - expected a mapping"


def test_error_invalid_yaml():
    with pytest.raises(ConfigError) as ie:
        KeyValue("test", "{...")
    assert str(ie.value) == "test invalid: not yaml or json format"
