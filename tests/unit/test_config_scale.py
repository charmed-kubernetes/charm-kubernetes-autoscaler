import pytest

from config.scale import JujuScale
from errors import JujuConfigError


def test_default_scale():
    assert JujuScale("").args(None) == []


def test_comma_separated_string():
    scale = JujuScale("3:5:kubernetes-worker,0:10:kubernetes-worker-gpu,")
    assert scale.args("test") == ["3:5:test:kubernetes-worker", "0:10:test:kubernetes-worker-gpu"]


def test_list_of_strings_yaml():
    scale = JujuScale("---\n" "- 3:5:kubernetes-worker\n" "- 0:10:kubernetes-worker-gpu\n")
    assert scale.args("test") == ["3:5:test:kubernetes-worker", "0:10:test:kubernetes-worker-gpu"]


def test_list_of_mappings_and_string_yaml():
    scale = JujuScale(
        "---\n"
        "- min: 3\n"
        "  max: 5\n"
        "  application: kubernetes-worker\n"
        "- 0:10:kubernetes-worker-gpu\n"
    )
    assert scale.args("test") == ["3:5:test:kubernetes-worker", "0:10:test:kubernetes-worker-gpu"]


def test_list_of_strings_json():
    scale = JujuScale('["3:5:kubernetes-worker","0:10:kubernetes-worker-gpu",]')
    assert scale.args("test") == ["3:5:test:kubernetes-worker", "0:10:test:kubernetes-worker-gpu"]


def test_yaml_with_model_part():
    scale = JujuScale("- 0:10:cdcaed9f-336d-47d3-83ba-d9ea9047b18c:kubernetes-worker-gpu")
    assert scale.args(None) == ["0:10:cdcaed9f-336d-47d3-83ba-d9ea9047b18c:kubernetes-worker-gpu"]


def test_error_yaml_mapping():
    with pytest.raises(JujuConfigError) as ie:
        JujuScale("{min: 0, max: 2, application: kubernetes-worker}")
    assert str(ie.value) == "juju_scale invalid: yaml or json format - expected a list"


def test_error_invalid_yaml():
    with pytest.raises(JujuConfigError) as ie:
        JujuScale("{...")
    assert str(ie.value) == "juju_scale invalid: not yaml or json format"


def test_error_invalid_yaml_type():
    with pytest.raises(JujuConfigError) as ie:
        JujuScale("- []")
    assert str(ie.value) == "juju_scale invalid: Unexpected yaml collection type"


def test_error_missing_element():
    with pytest.raises(JujuConfigError) as ie:
        JujuScale("---\n" "- min: 3\n" "  max: 5\n")
    assert str(ie.value) == "juju_scale invalid: missing required element 'application'"


def test_error_max_gt_min():
    with pytest.raises(JujuConfigError) as ie:
        JujuScale("5:3:kubernetes-worker,")
    assert (
        str(ie.value)
        == "juju_scale invalid: <min> should be less than <max> '5:3:kubernetes-worker'"
    )


def test_error_min_not_an_int():
    args = "X:3:kubernetes-worker"
    with pytest.raises(JujuConfigError) as ie:
        JujuScale(args)
    assert (
        str(ie.value)
        == f"juju_scale invalid: <min> & <max> must be non-negative integers '{args}'"
    )


def test_error_not_enough_parts():
    args = "0:kubernetes-worker"
    with pytest.raises(JujuConfigError) as ie:
        JujuScale(args)
    assert (
        str(ie.value)
        == f"juju_scale invalid: Must contain at least 3 parts <min>:<max>:<application> '{args}'"
    )


def test_error_too_many_parts():
    args = "0:1:2:3:kubernetes-worker"
    with pytest.raises(JujuConfigError) as ie:
        JujuScale(args)
    assert (
        str(ie.value)
        == f"juju_scale invalid: Must contain 4 parts <min>:<max>:<model>:<application> '{args}'"
    )


def test_error_model_invalid_part():
    args = "0:1:2:kubernetes-worker"
    with pytest.raises(JujuConfigError) as ie:
        JujuScale(args)
    assert str(ie.value) == f"juju_scale invalid: Invalid model part '{args}'"
