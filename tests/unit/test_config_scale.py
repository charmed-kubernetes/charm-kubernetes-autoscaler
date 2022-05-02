import pytest

from config.scale import ConfigScale
from errors import ConfigError


def test_default_scale():
    assert ConfigScale("").nodes(None) == []


def test_json_list():
    scale = ConfigScale(
        "["
        '{"min": 3, "max":5, "application": "kubernetes-worker"},'
        '{"min": 1, "max":10, "application": "kubernetes-worker-gpu"}'
        "]"
    )
    assert scale.nodes("test") == ["3:5:test:kubernetes-worker", "1:10:test:kubernetes-worker-gpu"]


def test_list_of_mappings_and_json_yaml():
    scale = ConfigScale(
        "---\n"
        "- min: 3\n"
        "  max: 5\n"
        "  application: kubernetes-worker\n"
        '- {"min": 1, "max":10, "application": "kubernetes-worker-gpu"}\n'
    )
    assert scale.nodes("test") == ["3:5:test:kubernetes-worker", "1:10:test:kubernetes-worker-gpu"]


def test_yaml_with_model_part():
    scale = ConfigScale(
        "---\n"
        "- min: 1\n"
        "  max: 10\n"
        "  model: cdcaed9f-336d-47d3-83ba-d9ea9047b18c\n"
        "  application: kubernetes-worker-gpu\n"
    )
    assert scale.nodes(None) == ["1:10:cdcaed9f-336d-47d3-83ba-d9ea9047b18c:kubernetes-worker-gpu"]


def test_error_yaml_mapping():
    with pytest.raises(ConfigError) as ie:
        ConfigScale("{min: 1, max: 2, application: kubernetes-worker}")
    assert str(ie.value) == "juju_scale invalid: yaml or json format - expected a list"


def test_error_invalid_yaml():
    with pytest.raises(ConfigError) as ie:
        ConfigScale("{...")
    assert str(ie.value) == "juju_scale invalid: not yaml or json format"


def test_error_invalid_yaml_type():
    with pytest.raises(ConfigError) as ie:
        ConfigScale("- []")
    assert str(ie.value) == "juju_scale invalid: Unexpected yaml collection type"


@pytest.mark.parametrize(
    "cfg, missing_element",
    [
        ("{max: 0, application: kubernetes-worker}", "min"),
        ("{min: 0, application: kubernetes-worker}", "max"),
        ("{min: 0, max: 5}", "application"),
    ],
)
def test_error_missing_element(cfg, missing_element):
    with pytest.raises(ConfigError) as ie:
        ConfigScale(f"- {cfg}")
    assert str(ie.value).startswith(
        f"juju_scale invalid: missing required element '{missing_element}'"
    )


def test_error_max_gt_min():
    with pytest.raises(ConfigError) as ie:
        ConfigScale("- {min: 5, max: 3, application: kubernetes-worker}")
    assert str(ie.value).startswith("juju_scale invalid: <min> should be less than <max> -")


def test_error_min_not_an_int():
    cfg = "- {min: X, max: 3, application: kubernetes-worker}"
    with pytest.raises(ConfigError) as ie:
        ConfigScale(cfg)
    assert str(ie.value).startswith(
        "juju_scale invalid: <min> & <max> must be non-negative, non-zero integers -"
    )


def test_error_min_lte_0():
    cfg = "- {min: 0, max: 3, application: kubernetes-worker}"
    with pytest.raises(ConfigError) as ie:
        ConfigScale(cfg)
    assert str(ie.value).startswith(
        "juju_scale invalid: <min> & <max> must be non-negative, non-zero integers -"
    )

    cfg = "- {min: -1, max: 3, application: kubernetes-worker}"
    with pytest.raises(ConfigError) as ie:
        ConfigScale(cfg)
    assert str(ie.value).startswith(
        "juju_scale invalid: <min> & <max> must be non-negative, non-zero integers -"
    )


def test_error_model_invalid():
    cfg = "- {min: 1, max: 2, model: 2, application: kubernetes-worker}"
    with pytest.raises(ConfigError) as ie:
        ConfigScale(cfg)
    assert str(ie.value).startswith("juju_scale invalid: Invalid model uuid - ")
