from unittest import IsolatedAsyncioTestCase, skip
from unittest.mock import AsyncMock, patch

from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_MEDIUM,
    FAN_LOW,
    HVAC_MODE_DRY,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_HUMIDITY,
)
from homeassistant.components.humidifier.const import (
    MODE_NORMAL,
    MODE_BOOST,
    MODE_SLEEP,
)
from homeassistant.components.switch import DEVICE_CLASS_SWITCH
from homeassistant.const import STATE_UNAVAILABLE

from custom_components.tuya_local.generic.climate import TuyaLocalClimate
from custom_components.tuya_local.generic.switch import TuyaLocalSwitch
from custom_components.tuya_local.helpers.device_config import TuyaDeviceConfig

from ..const import EANONS_HUMIDIFIER_PAYLOAD
from ..helpers import assert_device_properties_set

FANMODE_DPS = "2"
TIMERHR_DPS = "3"
TIMER_DPS = "4"
ERROR_DPS = "9"
HVACMODE_DPS = "10"
PRESET_DPS = "12"
HUMIDITY_DPS = "15"
CURRENTHUMID_DPS = "16"
SWITCH_DPS = "22"


class TestEanonsHumidifier(IsolatedAsyncioTestCase):
    def setUp(self):
        device_patcher = patch("custom_components.tuya_local.device.TuyaLocalDevice")
        self.addCleanup(device_patcher.stop)
        self.mock_device = device_patcher.start()
        cfg = TuyaDeviceConfig("eanons_humidifier.yaml")
        entities = {}
        entities[cfg.primary_entity.entity] = cfg.primary_entity
        for e in cfg.secondary_entities():
            entities[e.entity] = e

        self.climate_name = (
            "missing" if "climate" not in entities else entities["climate"].name
        )
        self.switch_name = (
            "missing" if "switch" not in entities else entities["switch"].name
        )

        self.subject = TuyaLocalClimate(self.mock_device(), entities.get("climate"))
        self.switch = TuyaLocalSwitch(self.mock_device(), entities.get("switch"))

        self.dps = EANONS_HUMIDIFIER_PAYLOAD.copy()
        self.subject._device.get_property.side_effect = lambda id: self.dps[id]

    def test_supported_features(self):
        self.assertEqual(
            self.subject.supported_features,
            SUPPORT_TARGET_HUMIDITY | SUPPORT_PRESET_MODE | SUPPORT_FAN_MODE,
        )

    def test_shouldPoll(self):
        self.assertTrue(self.subject.should_poll)
        self.assertTrue(self.switch.should_poll)

    def test_name_returns_device_name(self):
        self.assertEqual(self.subject.name, self.subject._device.name)
        self.assertEqual(self.switch.name, self.subject._device.name)

    def test_friendly_name_returns_config_name(self):
        self.assertEqual(self.subject.friendly_name, self.climate_name)
        self.assertEqual(self.switch.friendly_name, self.switch_name)

    def test_unique_id_returns_device_unique_id(self):
        self.assertEqual(self.subject.unique_id, self.subject._device.unique_id)
        self.assertEqual(self.switch.unique_id, self.subject._device.unique_id)

    def test_device_info_returns_device_info_from_device(self):
        self.assertEqual(self.subject.device_info, self.subject._device.device_info)
        self.assertEqual(self.switch.device_info, self.subject._device.device_info)

    @skip("Icon customisation not supported yet")
    def test_icon_is_humidifier(self):
        """Test that the icon is as expected."""
        self.dps[HVACMODE_DPS] = True
        self.assertEqual(self.subject.icon, "mdi:air-humidifier")

        self.dps[HVACMODE_DPS] = False
        self.assertEqual(self.subject.icon, "mdi:air-humidifier-off")

    def test_current_humidity(self):
        self.dps[CURRENTHUMID_DPS] = 47
        self.assertEqual(self.subject.current_humidity, 47)

    def test_min_target_humidity(self):
        self.assertEqual(self.subject.min_humidity, 40)

    def test_max_target_humidity(self):
        self.assertEqual(self.subject.max_humidity, 90)

    def test_target_humidity(self):
        self.dps[HUMIDITY_DPS] = 55
        self.assertEqual(self.subject.target_humidity, 55)

    def test_hvac_mode(self):
        self.dps[HVACMODE_DPS] = True
        self.assertEqual(self.subject.hvac_mode, HVAC_MODE_DRY)

        self.dps[HVACMODE_DPS] = False
        self.assertEqual(self.subject.hvac_mode, HVAC_MODE_OFF)

        self.dps[HVACMODE_DPS] = None
        self.assertEqual(self.subject.hvac_mode, STATE_UNAVAILABLE)

    def test_hvac_modes(self):
        self.assertCountEqual(self.subject.hvac_modes, [HVAC_MODE_OFF, HVAC_MODE_DRY])

    async def test_turn_on(self):
        async with assert_device_properties_set(
            self.subject._device, {HVACMODE_DPS: True}
        ):
            await self.subject.async_set_hvac_mode(HVAC_MODE_DRY)

    async def test_turn_off(self):
        async with assert_device_properties_set(
            self.subject._device, {HVACMODE_DPS: False}
        ):
            await self.subject.async_set_hvac_mode(HVAC_MODE_OFF)

    def test_preset_mode(self):
        self.dps[PRESET_DPS] = "sleep"
        self.assertEqual(self.subject.preset_mode, MODE_SLEEP)

        self.dps[PRESET_DPS] = "humidity"
        self.assertEqual(self.subject.preset_mode, MODE_NORMAL)

        self.dps[PRESET_DPS] = "work"
        self.assertEqual(self.subject.preset_mode, MODE_BOOST)

        self.dps[PRESET_DPS] = None
        self.assertEqual(self.subject.preset_mode, None)

    def test_preset_modes(self):
        self.assertCountEqual(
            self.subject.preset_modes,
            {MODE_NORMAL, MODE_SLEEP, MODE_BOOST},
        )

    async def test_set_preset_to_normal(self):
        async with assert_device_properties_set(
            self.subject._device,
            {
                PRESET_DPS: "humidity",
            },
        ):
            await self.subject.async_set_preset_mode(MODE_NORMAL)
            self.subject._device.anticipate_property_value.assert_not_called()

    async def test_set_preset_to_sleep(self):
        async with assert_device_properties_set(
            self.subject._device,
            {
                PRESET_DPS: "sleep",
            },
        ):
            await self.subject.async_set_preset_mode(MODE_SLEEP)
            self.subject._device.anticipate_property_value.assert_not_called()

    async def test_set_preset_to_boost(self):
        async with assert_device_properties_set(
            self.subject._device,
            {
                PRESET_DPS: "work",
            },
        ):
            await self.subject.async_set_preset_mode(MODE_BOOST)
            self.subject._device.anticipate_property_value.assert_not_called()

    def test_device_state_attributes(self):
        self.dps[ERROR_DPS] = 0
        self.dps[TIMERHR_DPS] = "cancel"
        self.dps[TIMER_DPS] = 0
        self.assertCountEqual(
            self.subject.device_state_attributes,
            {
                "error": "OK",
                "timer_hr": "cancel",
                "timer_min": 0,
            },
        )

        self.dps[ERROR_DPS] = 1
        self.dps[TIMERHR_DPS] = "1"
        self.dps[TIMER_DPS] = 60
        self.assertCountEqual(
            self.subject.device_state_attributes,
            {
                "error": 1,
                "timer_hr": "1",
                "timer_min": 60,
            },
        )

    def test_fan_mode(self):
        self.dps[FANMODE_DPS] = "small"
        self.assertEqual(self.subject.fan_mode, FAN_LOW)

        self.dps[FANMODE_DPS] = "middle"
        self.assertEqual(self.subject.fan_mode, FAN_MEDIUM)

        self.dps[FANMODE_DPS] = "large"
        self.assertEqual(self.subject.fan_mode, FAN_HIGH)

        self.dps[FANMODE_DPS] = None
        self.assertEqual(self.subject.fan_mode, None)

    def test_fan_modes(self):
        self.assertCountEqual(
            self.subject.fan_modes,
            {FAN_LOW, FAN_MEDIUM, FAN_HIGH},
        )

    async def test_set_fan_mode(self):
        async with assert_device_properties_set(
            self.subject._device,
            {FANMODE_DPS: "small"},
        ):
            await self.subject.async_set_fan_mode(FAN_LOW)

    def test_switch_was_created(self):
        self.assertIsInstance(self.switch, TuyaLocalSwitch)

    def test_switch_is_same_device(self):
        self.assertEqual(self.switch._device, self.subject._device)

    def test_switch_class_is_switch(self):
        self.assertEqual(self.switch.device_class, DEVICE_CLASS_SWITCH)

    def test_switch_is_on(self):
        self.dps[SWITCH_DPS] = True
        self.assertTrue(self.switch.is_on)

        self.dps[SWITCH_DPS] = False
        self.assertFalse(self.switch.is_on)

    def test_switch_is_on_when_unavailable(self):
        self.dps[SWITCH_DPS] = None
        self.assertEqual(self.switch.is_on, STATE_UNAVAILABLE)

    async def test_switch_turn_on(self):
        async with assert_device_properties_set(
            self.switch._device, {SWITCH_DPS: True}
        ):
            await self.switch.async_turn_on()

    async def test_switch_turn_off(self):
        async with assert_device_properties_set(
            self.switch._device, {SWITCH_DPS: False}
        ):
            await self.switch.async_turn_off()

    async def test_toggle_turns_the_switch_on_when_it_was_off(self):
        self.dps[SWITCH_DPS] = False

        async with assert_device_properties_set(
            self.switch._device, {SWITCH_DPS: True}
        ):
            await self.switch.async_toggle()

    async def test_toggle_turns_the_switch_off_when_it_was_on(self):
        self.dps[SWITCH_DPS] = True

        async with assert_device_properties_set(
            self.switch._device, {SWITCH_DPS: False}
        ):
            await self.switch.async_toggle()

    def test_switch_state_attributes_set(self):
        self.assertEqual(self.switch.device_state_attributes, {})
