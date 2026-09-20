

from typing import Any
from unittest.mock import call, patch

import pytest

from homeassistant.components import mqtt, sensor
from homeassistant.components.mqtt.sensor import DEFAULT_NAME as DEFAULT_SENSOR_NAME
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.util import slugify

from .common import (
    MOCK_NOTIFY_SUBENTRY_DATA,
    MOCK_SUBENTRY_DATA_BAD_COMPONENT_SCHEMA,
    MOCK_SUBENTRY_DATA_SET_MIX,
)

from tests.common import MockConfigEntry, async_capture_events, async_fire_mqtt_message
from tests.typing import MqttMockHAClientGenerator


@pytest.mark.parametrize(
    "hass_config",
    [
        {
            mqtt.DOMAIN: {
                sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "availability_topic": "test-topic",
                    "payload_available": True,
                    "payload_not_available": False,
                    "value_template": "{{ int(value) or '' }}",
                    "availability_template": "{{ value != '0' }}",
                }
            }
        }
    ],
)
async def test_availability_with_shared_state_topic(
    hass: HomeAssistant, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:





    await mqtt_mock_entry()

    events = []

    @callback
    def test_callback(event) -> None:
        events.append(event)

    hass.bus.async_listen(EVENT_STATE_CHANGED, test_callback)

    async_fire_mqtt_message(hass, "test-topic", "100")
    await hass.async_block_till_done()

    assert len(events) == 1

    events.clear()
    async_fire_mqtt_message(hass, "test-topic", "50")
    await hass.async_block_till_done()
    assert len(events) == 1

    events.clear()
    async_fire_mqtt_message(hass, "test-topic", "0")
    await hass.async_block_till_done()


    assert len(events) == 1

    events.clear()
    async_fire_mqtt_message(hass, "test-topic", "10")
    await hass.async_block_till_done()


    assert len(events) == 1


@pytest.mark.parametrize(
    (
        "hass_config",
        "entity_id",
        "friendly_name",
        "device_name",
        "assert_log",
    ),
    [
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device": {"identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.mqtt_sensor",
            DEFAULT_SENSOR_NAME,
            None,
            True,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device": {"name": "Test", "identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.test_mqtt_sensor",
            "Test MQTT Sensor",
            "Test",
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {"name": "Test", "identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.test_humidity",
            "Test Humidity",
            "Test",
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {"identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.humidity",
            "Humidity",
            None,
            True,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "name": "MySensor",
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {"name": "Test", "identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.test_mysensor",
            "Test MySensor",
            "Test",
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "name": "MySensor",
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {"identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.mysensor",
            "MySensor",
            None,
            True,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "name": None,
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {"name": "Test", "identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.test",
            "Test",
            "Test",
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "name": None,
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {"identifiers": ["helloworld"]},
                    }
                }
            },
            "sensor.mqtt_veryunique",
            "mqtt veryunique",
            None,
            True,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "name": "Hello world",
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {
                            "identifiers": ["helloworld"],
                            "name": "Hello world",
                        },
                    }
                }
            },
            "sensor.hello_world_hello_world",
            "Hello world Hello world",
            "Hello world",
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "name": "World automation",
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {
                            "identifiers": ["helloworld"],
                            "name": "World",
                        },
                    }
                }
            },
            "sensor.world_world_automation",
            "World World automation",
            "World",
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    sensor.DOMAIN: {
                        "name": "world automation",
                        "state_topic": "test-topic",
                        "unique_id": "veryunique",
                        "device_class": "humidity",
                        "device": {
                            "identifiers": ["helloworld"],
                            "name": "world",
                        },
                    }
                }
            },
            "sensor.world_world_automation",
            "world world automation",
            "world",
            False,
        ),
    ],
    ids=[
        "default_entity_name_without_device_name",
        "default_entity_name_with_device_name",
        "name_follows_device_class",
        "name_follows_device_class_without_device_name",
        "name_overrides_device_class",
        "name_set_no_device_name_set",
        "none_entity_name_with_device_name",
        "none_entity_name_without_device_name",
        "entity_name_and_device_name_the_same",
        "entity_name_startswith_device_name1",
        "entity_name_startswith_device_name2",
    ],
)
@patch("homeassistant.components.mqtt.client.DISCOVERY_COOLDOWN", 0.0)
@pytest.mark.usefixtures("mqtt_client_mock")
async def test_default_entity_and_device_name(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    caplog: pytest.LogCaptureFixture,
    entity_id: str,
    friendly_name: str,
    device_name: str | None,
    assert_log: bool,
) -> None:





    events = async_capture_events(hass, ir.EVENT_REPAIRS_ISSUE_REGISTRY_UPDATED)
    hass.set_state(CoreState.starting)
    await hass.async_block_till_done()

    entry = MockConfigEntry(
        domain=mqtt.DOMAIN,
        data={mqtt.CONF_BROKER: "mock-broker"},
        version=mqtt.CONFIG_ENTRY_VERSION,
        minor_version=mqtt.CONFIG_ENTRY_MINOR_VERSION,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    device = device_registry.async_get_device({("mqtt", "helloworld")})
    assert device is not None
    assert device.name == device_name

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.name == friendly_name

    assert (
        "MQTT device information always needs to include a name" in caplog.text
    ) is assert_log


    assert len(events) == 0
    await hass.async_block_till_done(wait_background_tasks=True)

    assert len(events) == 0


async def test_name_attribute_is_set_or_not(
    hass: HomeAssistant, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:




    await mqtt_mock_entry()
    async_fire_mqtt_message(
        hass,
        "homeassistant/binary_sensor/bla/config",
        '{ "name": "Gate", "state_topic": "test-topic", "device_class": "door", '
        '"default_entity_id": "binary_sensor.gate",'
        '"device": {"identifiers": "very_unique", "name": "xyz_door_sensor"}'
        "}",
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.gate")

    assert state is not None
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Gate"


    async_fire_mqtt_message(
        hass,
        "homeassistant/binary_sensor/bla/config",
        '{ "state_topic": "test-topic", "device_class": "door", '
        '"default_entity_id": "binary_sensor.gate",'
        '"device": {"identifiers": "very_unique", "name": "xyz_door_sensor"}'
        "}",
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.gate")

    assert state is not None
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Door"


    async_fire_mqtt_message(
        hass,
        "homeassistant/binary_sensor/bla/config",
        '{ "name": null, "state_topic": "test-topic", "device_class": "door", '
        '"default_entity_id": "binary_sensor.gate",'
        '"device": {"identifiers": "very_unique", "name": "xyz_door_sensor"}'
        "}",
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.gate")

    assert state is not None
    assert state.attributes.get(ATTR_FRIENDLY_NAME) is None


@pytest.mark.parametrize(
    "hass_config",
    [
        {
            mqtt.DOMAIN: {
                sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "state-topic",
                    "availability_topic": "test-topic",
                    "availability_template": "{{ value_json.some_var * 1 }}",
                }
            }
        },
        {
            mqtt.DOMAIN: {
                sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "state-topic",
                    "availability": {
                        "topic": "test-topic",
                        "value_template": "{{ value_json.some_var * 1 }}",
                    },
                }
            }
        },
        {
            mqtt.DOMAIN: {
                sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "state-topic",
                    "json_attributes_topic": "test-topic",
                    "json_attributes_template": "{{ value_json.some_var * 1 }}",
                }
            }
        },
    ],
    ids=[
        "availability_template1",
        "availability_template2",
        "json_attributes_template",
    ],
)
async def test_value_template_fails(
    hass: HomeAssistant,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:

    await mqtt_mock_entry()
    async_fire_mqtt_message(hass, "test-topic", '{"some_var": null }')
    assert (
        "TypeError: unsupported operand type(s) for *: 'NoneType' and 'int' rendering template"
        in caplog.text
    )


@pytest.mark.parametrize(
    "mqtt_config_subentries_data",
    [
        (
            ConfigSubentryData(
                data=MOCK_SUBENTRY_DATA_SET_MIX,
                subentry_type="device",
                title="Mock subentry",
            ),
        )
    ],
)
async def test_loading_subentries(
    hass: HomeAssistant,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    mqtt_config_subentries_data: tuple[dict[str, Any]],
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:

    await mqtt_mock_entry()
    entry = hass.config_entries.async_entries(mqtt.DOMAIN)[0]
    subentry_id = next(iter(entry.subentries))

    device = device_registry.async_get_device({("mqtt", subentry_id)})
    assert device is not None
    for object_id, component in mqtt_config_subentries_data[0]["data"][
        "components"
    ].items():
        platform = component["platform"]
        entity_id = f"{platform}.{slugify(device.name)}_{slugify(component['name'])}"
        entity_entry_entity_id = entity_registry.async_get_entity_id(
            platform, mqtt.DOMAIN, f"{subentry_id}_{object_id}"
        )
        assert entity_entry_entity_id == entity_id
        state = hass.states.get(entity_id)
        assert state is not None
        assert (
            state.attributes.get("entity_picture") == f"https://example.com/{object_id}"
        )

        assert state.state == "unavailable"


    async_fire_mqtt_message(hass, "test/availability", '{"availability": "online"}')
    for component in mqtt_config_subentries_data[0]["data"]["components"].values():
        platform = component["platform"]
        entity_id = f"{platform}.{slugify(device.name)}_{slugify(component['name'])}"
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unknown"


@pytest.mark.parametrize(
    "mqtt_config_subentries_data",
    [
        (
            ConfigSubentryData(
                data=MOCK_SUBENTRY_DATA_BAD_COMPONENT_SCHEMA,
                subentry_type="device",
                title="Mock subentry",
            ),
        )
    ],
)
async def test_loading_subentry_with_bad_component_schema(
    hass: HomeAssistant,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    mqtt_config_subentries_data: tuple[dict[str, Any]],
    device_registry: dr.DeviceRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:

    await mqtt_mock_entry()
    entry = hass.config_entries.async_entries(mqtt.DOMAIN)[0]
    subentry_id = next(iter(entry.subentries))

    device = device_registry.async_get_device({("mqtt", subentry_id)})
    assert device is None
    assert (
        "Schema violation occurred when trying to set up entity from subentry"
        in caplog.text
    )


@pytest.mark.parametrize(
    "mqtt_config_subentries_data",
    [
        (
            ConfigSubentryData(
                data=MOCK_NOTIFY_SUBENTRY_DATA,
                subentry_type="device",
                title="Mock subentry",
            ),
        )
    ],
)
async def test_qos_on_mqt_device_from_subentry(
    hass: HomeAssistant,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    mqtt_config_subentries_data: tuple[dict[str, Any]],
    device_registry: dr.DeviceRegistry,
) -> None:

    mqtt_mock = await mqtt_mock_entry()
    entry = hass.config_entries.async_entries(mqtt.DOMAIN)[0]
    subentry_id = next(iter(entry.subentries))

    device = device_registry.async_get_device({("mqtt", subentry_id)})
    assert device is not None
    assert hass.states.get("notify.milk_notifier_milkman_alert") is not None
    await hass.services.async_call(
        "notify",
        "send_message",
        {"entity_id": "notify.milk_notifier_milkman_alert", "message": "Test message"},
    )
    await hass.async_block_till_done()
    assert len(mqtt_mock.async_publish.mock_calls) == 1
    mqtt_mock.async_publish.mock_calls[0] = call("test-topic", "Test message", 1, False)
