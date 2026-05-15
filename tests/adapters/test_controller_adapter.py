from app.adapters import controller
from app.adapters.controller import controller_manager


def test_controller_entry_exports_public_names():
    assert controller.PROTO_PYGAME == "pygame"
    assert controller.PROTO_XINPUT == "xinput"
    assert controller.LAYOUT_XBOX == "xbox"
    assert controller.LAYOUT_PS == "ps"
    assert controller.LAYOUT_PS_EDGE == "ps_edge"
    assert controller.LAYOUT_SWITCH == "switch"
    assert controller.LAYOUT_GENERIC == "generic"
    assert controller.MAX_SLOTS == 4
    assert controller.LOGICAL_BUTTONS
    assert controller.ControllerInfo
    assert controller.ControllerState
    assert controller.ControllerManager
    assert controller.get_button_display_name
    assert controller.get_button_options_for_layout


def test_button_options_filter_absent_buttons():
    options = controller.get_button_options_for_layout(controller.LAYOUT_XBOX)
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
    raw_map = controller.get_pygame_button_map(
        controller.LAYOUT_XBOX,
        num_hats=1,
        num_buttons=11,
    )
    sdl_map = controller.get_pygame_button_map(
        controller.LAYOUT_XBOX,
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
    state = controller.ControllerState()

    assert state.lx == 0.0
    assert state.ly == 0.0
    assert state.rx == 0.0
    assert state.ry == 0.0
    assert state.lt == 0.0
    assert state.rt == 0.0
    assert state.buttons == {}
    assert isinstance(state.buttons, dict)


def test_controller_manager_prefers_xinput_for_xbox_style_devices(monkeypatch):
    class FakePygameBackend:
        def is_available(self):
            return True

        def scan(self):
            return [
                {
                    "name": "Xbox Wireless Controller",
                    "guid": "pg-xbox",
                    "handle": "pg-xbox-handle",
                    "num_axes": 6,
                    "num_buttons": 15,
                    "num_hats": 0,
                },
                {
                    "name": "DualSense Wireless Controller",
                    "guid": "pg-ps",
                    "handle": "pg-ps-handle",
                    "num_axes": 6,
                    "num_buttons": 16,
                    "num_hats": 1,
                },
            ]

        def detect_layout(self, name, num_buttons):
            if "DualSense" in name:
                return controller.LAYOUT_PS
            return controller.LAYOUT_XBOX

        def read_state(self, _info):
            return controller.ControllerState(rx=0.1)

    class FakeXInputBackend:
        def is_available(self):
            return True

        def scan(self):
            return [
                {
                    "index": 0,
                    "name": "XInput Controller",
                    "guid": "xinput_0",
                    "handle": 0,
                    "num_axes": 6,
                    "num_buttons": 14,
                    "num_hats": 0,
                }
            ]

        def read_state(self, _info):
            return controller.ControllerState(rx=0.9)

    monkeypatch.setattr(controller_manager, "PygameBackend", FakePygameBackend)
    monkeypatch.setattr(controller_manager, "XInputBackend", FakeXInputBackend)

    manager = controller_manager.ControllerManager()
    message = manager.scan_and_assign()

    assert message == "扫描完成：检测到 2 个手柄"
    assert manager.slots[0].name == "Xbox Wireless Controller"
    assert manager.slots[0].protocol == controller.PROTO_XINPUT
    assert manager.slots[0].layout == controller.LAYOUT_XBOX
    assert manager.slots[1].name == "DualSense Wireless Controller"
    assert manager.slots[1].protocol == controller.PROTO_PYGAME
    assert manager.slots[1].layout == controller.LAYOUT_PS
    assert manager.get_current_slot() == 0
    assert manager.read_state(manager.slots[0]).rx == 0.9
    assert manager.read_state(manager.slots[1]).rx == 0.1


def test_controller_manager_keeps_existing_slot_and_clears_missing_current(monkeypatch):
    class FakePygameBackend:
        devices = [
            {
                "name": "DualSense Wireless Controller",
                "guid": "pg-ps",
                "handle": "new-handle",
                "num_axes": 6,
                "num_buttons": 16,
                "num_hats": 1,
            }
        ]

        def is_available(self):
            return True

        def scan(self):
            return list(self.devices)

        def detect_layout(self, _name, _num_buttons):
            return controller.LAYOUT_PS

    class FakeXInputBackend:
        def is_available(self):
            return False

        def scan(self):
            return []

    monkeypatch.setattr(controller_manager, "PygameBackend", FakePygameBackend)
    monkeypatch.setattr(controller_manager, "XInputBackend", FakeXInputBackend)

    manager = controller_manager.ControllerManager()
    manager.slots[2] = controller.ControllerInfo(
        slot=2,
        name="DualSense Wireless Controller",
        protocol=controller.PROTO_PYGAME,
        layout=controller.LAYOUT_PS,
        guid="pg-ps",
        handle="old-handle",
    )
    manager.set_current_slot(2)

    manager.scan_and_assign()

    assert manager.slots[2] is not None
    assert manager.slots[2].handle == "new-handle"
    assert manager.get_current_slot() == 2

    FakePygameBackend.devices = []
    manager.scan_and_assign()

    assert manager.slots[2] is None
    assert manager.get_current_slot() is None
