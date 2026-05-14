import controller_backend as compat
from stick_analyzer.adapters import controller


def test_compat_entry_exports_legacy_public_names():
    assert compat.PROTO_PYGAME == "pygame"
    assert compat.PROTO_XINPUT == "xinput"
    assert compat.LAYOUT_XBOX == "xbox"
    assert compat.LAYOUT_PS == "ps"
    assert compat.LAYOUT_PS_EDGE == "ps_edge"
    assert compat.LAYOUT_SWITCH == "switch"
    assert compat.LAYOUT_GENERIC == "generic"
    assert compat.MAX_SLOTS == 4
    assert compat.LOGICAL_BUTTONS is controller.LOGICAL_BUTTONS
    assert compat.ControllerInfo is controller.ControllerInfo
    assert compat.ControllerState is controller.ControllerState
    assert compat.ControllerManager is controller.ControllerManager
    assert compat.get_button_display_name is controller.get_button_display_name
    assert compat.get_button_options_for_layout is controller.get_button_options_for_layout


def test_button_options_filter_absent_buttons():
    options = compat.get_button_options_for_layout(compat.LAYOUT_XBOX)
    logical_codes = [logical for _display, logical in options]
    display_names = [display for display, _logical in options]

    assert "TOUCHPAD" not in logical_codes
    assert "EDGE_FN1" not in logical_codes
    assert "EDGE_FN2" not in logical_codes
    assert "EDGE_RB1" not in logical_codes
    assert "EDGE_RB2" not in logical_codes
    assert "TRIGGER_LEFT" in logical_codes
    assert "TRIGGER_RIGHT" in logical_codes
    assert all(display != "(无)" for display in display_names)


def test_xbox_raw_and_sdl_gamecontroller_button_maps_differ():
    raw_map = compat.get_pygame_button_map(
        compat.LAYOUT_XBOX,
        num_hats=1,
        num_buttons=11,
    )
    sdl_map = compat.get_pygame_button_map(
        compat.LAYOUT_XBOX,
        num_hats=0,
        num_buttons=15,
    )

    assert raw_map[4] == "LEFT_SHOULDER"
    assert raw_map[5] == "RIGHT_SHOULDER"
    assert 11 not in raw_map
    assert sdl_map[4] == "BACK"
    assert sdl_map[9] == "LEFT_SHOULDER"
    assert sdl_map[10] == "RIGHT_SHOULDER"
    assert sdl_map[11] == "DPAD_UP"


def test_controller_state_default_is_constructable():
    state = compat.ControllerState()

    assert state.lx == 0.0
    assert state.ly == 0.0
    assert state.rx == 0.0
    assert state.ry == 0.0
    assert state.lt == 0.0
    assert state.rt == 0.0
    assert state.buttons == {}
    assert isinstance(state.buttons, dict)
