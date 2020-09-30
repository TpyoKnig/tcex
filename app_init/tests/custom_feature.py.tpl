# -*- coding: utf-8 -*-
"""Custom test method feature class."""
from ..custom import Custom  # pylint: disable=relative-beyond-top-level


# pylint: disable=no-self-use,unused-argument,useless-super-delegation
class CustomFeature(Custom):
    """Custom test method class Apps."""

    def __init__(self, **kwargs):
        """Initialize class properties."""
        super(CustomFeature, self).__init__(**kwargs)

    def setup_class(self, test_feature: object) -> None:
        """Run setup class code."""
        super(CustomFeature, self).setup_class(test_feature)

    def setup_method(self, test_feature: object) -> None:
        """Run setup method code."""
        super(CustomFeature, self).setup_method(test_feature)

    def teardown_class(self, test_feature: object) -> None:
        """Run teardown class code."""
        super(CustomFeature, self).teardown_class(test_feature)

    def teardown_method(self, test_feature: object) -> None:
        """Run teardown method code."""
        super(CustomFeature, self).teardown_method(test_feature)

    % if runtime_level in ['triggerservice']:
    def trigger_method(self, test_feature: object, profile_data: dict, monkeypatch: object) -> None:
        """Perform action to trigger the event."""
        super(CustomFeature, self).trigger_method(test_feature, profile_data, monkeypatch)

    def test_pre_create_config(
        self, test_feature: object, profile_data: dict, monkeypatch: object
    ) -> None:
        """Run test method code before create configs."""
        super(CustomFeature, self).test_pre_create_config(test_feature, profile_data, monkeypatch)

    def test_pre_delete_config(
        self, test_feature: object, profile_data: dict, monkeypatch: object
    ) -> None:
        """Run test method code before delete configs."""
        super(CustomFeature, self).test_pre_delete_config(test_feature, profile_data, monkeypatch)

    % elif runtime_level in ['webhooktriggerservice']:
    def test_pre_create_config(
        self, test_feature: object, profile_data: dict, monkeypatch: object
    ) -> None:
        """Run test method code before create configs."""
        super(CustomFeature, self).test_pre_create_config(test_feature, profile_data, monkeypatch)

    def test_pre_delete_config(
        self, test_feature: object, profile_data: dict, monkeypatch: object
    ) -> None:
        """Run test method code before delete configs."""
        super(CustomFeature, self).test_pre_delete_config(test_feature, profile_data, monkeypatch)

    def test_pre_webhook(
        self, test_feature: object, profile_data: dict, monkeypatch: object
    ) -> None:
        """Run test method code before webhook."""
        super(CustomFeature, self).test_pre_webhook(test_feature, profile_data, monkeypatch)

    % else:
    def test_pre_run(self, test_feature: object, profile_data: dict, monkeypatch: object) -> None:
        """Run test method code before App run method."""
        super(CustomFeature, self).test_pre_run(test_feature, profile_data, monkeypatch)

    def test_pre_validate(self, test_feature: object, profile_data: dict) -> None:
        """Run test method code before test validation."""
        super(CustomFeature, self).test_pre_validate(test_feature, profile_data)
    % endif
