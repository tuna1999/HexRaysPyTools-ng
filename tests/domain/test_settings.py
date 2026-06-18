"""Test settings.load_into."""
from hexrays_pytools.domain.session import Session
from hexrays_pytools.domain.settings import SETTING_KEYS, load_into


def test_setting_keys_listed() -> None:
    """SETTING_KEYS contains the 5 expected keys."""
    assert "log_level" in SETTING_KEYS
    assert "propagate_through_all_names" in SETTING_KEYS
    assert "store_xrefs" in SETTING_KEYS
    assert "scan_any_type" in SETTING_KEYS
    assert "templated_types_file" in SETTING_KEYS


def test_load_into_applies_log_level() -> None:
    """load_into maps the 'log_level' string setting to a logging constant."""
    import logging
    ida_settings = __import__("ida_settings")
    ida_settings.get_current_plugin_setting.side_effect = lambda k: "DEBUG" if k == "log_level" else None
    s = Session()
    load_into(s)
    assert s.log_level == logging.DEBUG


def test_load_into_applies_bool_settings() -> None:
    """load_into maps 'store_xrefs' and 'propagate_through_all_names' to booleans."""
    ida_settings = __import__("ida_settings")
    def fake(k: str) -> object:
        return {"store_xrefs": True, "propagate_through_all_names": True}.get(k)
    ida_settings.get_current_plugin_setting.side_effect = fake
    s = Session()
    load_into(s)
    assert s.store_xrefs is True
    assert s.propagate_through_all_names is True


def test_load_into_skips_none_values() -> None:
    """load_into leaves default values when HCLI returns None."""
    ida_settings = __import__("ida_settings")
    ida_settings.get_current_plugin_setting.return_value = None
    s = Session()
    s.store_xrefs = True  # set non-default
    load_into(s)
    # None is skipped, so default is preserved
    assert s.store_xrefs is True


def test_load_into_handles_ida_settings_exception() -> None:
    """load_into catches exceptions from ida_settings (e.g. in tests)."""
    ida_settings = __import__("ida_settings")
    ida_settings.get_current_plugin_setting.side_effect = RuntimeError("not initialized")
    s = Session()
    load_into(s)  # should not raise
    assert s.log_level == 20  # default INFO
