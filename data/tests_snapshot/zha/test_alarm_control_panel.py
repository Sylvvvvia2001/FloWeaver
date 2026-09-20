

from collections.abc import Callable, Coroutine
from unittest.mock import AsyncMock, call, patch, sentinel

import pytest
from zigpy.device import Device
from zigpy.profiles import zha
from zigpy.zcl import Cluster
from zigpy.zcl.clusters import security
import zigpy.zcl.foundation as zcl_f

from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_DOMAIN,
    AlarmControlPanelState,
)
from homeassistant.components.zha.helpers import (
    ZHADeviceProxy,
    ZHAGatewayProxy,
    get_zha_gateway,
    get_zha_gateway_proxy,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant

from .common import find_entity_id
from .conftest import SIG_EP_INPUT, SIG_EP_OUTPUT, SIG_EP_PROFILE, SIG_EP_TYPE


@pytest.fixture(autouse=True)
def alarm_control_panel_platform_only():

    with patch(
        "homeassistant.components.zha.PLATFORMS",
        (
            Platform.ALARM_CONTROL_PANEL,
            Platform.DEVICE_TRACKER,
            Platform.NUMBER,
            Platform.SELECT,
        ),
    ):
        yield


@patch(
    "zigpy.zcl.clusters.security.IasAce.client_command",
    new=AsyncMock(return_value=[sentinel.data, zcl_f.Status.SUCCESS]),
)
async def test_alarm_control_panel(
    hass: HomeAssistant,
    setup_zha: Callable[..., Coroutine[None]],
    zigpy_device_mock: Callable[..., Device],
) -> None:


    await setup_zha()
    gateway = get_zha_gateway(hass)
    gateway_proxy: ZHAGatewayProxy = get_zha_gateway_proxy(hass)

    zigpy_device = zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [],
                SIG_EP_OUTPUT: [security.IasAce.cluster_id],
                SIG_EP_TYPE: zha.DeviceType.IAS_ANCILLARY_CONTROL,
                SIG_EP_PROFILE: zha.PROFILE_ID,
            }
        },
        node_descriptor=b"\x02@\x8c\x02\x10RR\x00\x00\x00R\x00\x00",
    )

    gateway.get_or_create_device(zigpy_device)
    await gateway.async_device_initialized(zigpy_device)
    await hass.async_block_till_done(wait_background_tasks=True)

    zha_device_proxy: ZHADeviceProxy = gateway_proxy.get_device_proxy(zigpy_device.ieee)
    entity_id = find_entity_id(Platform.ALARM_CONTROL_PANEL, zha_device_proxy, hass)
    cluster = zigpy_device.endpoints[1].out_clusters[security.IasAce.cluster_id]
    assert entity_id is not None

    assert hass.states.get(entity_id).state == AlarmControlPanelState.DISARMED


    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_arm_away",
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY
    assert cluster.client_command.call_count == 2
    assert cluster.client_command.await_count == 2
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.Armed_Away,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.No_Alarm,
    )


    await reset_alarm_panel(hass, cluster, entity_id)


    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_arm_away",
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY
    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_disarm",
        {ATTR_ENTITY_ID: entity_id, "code": "1111"},
        blocking=True,
    )
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_disarm",
        {ATTR_ENTITY_ID: entity_id, "code": "1111"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED
    assert cluster.client_command.call_count == 4
    assert cluster.client_command.await_count == 4
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.In_Alarm,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.Emergency,
    )


    await reset_alarm_panel(hass, cluster, entity_id)


    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_arm_home",
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_HOME
    assert cluster.client_command.call_count == 2
    assert cluster.client_command.await_count == 2
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.Armed_Stay,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.No_Alarm,
    )


    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_arm_night",
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_NIGHT
    assert cluster.client_command.call_count == 2
    assert cluster.client_command.await_count == 2
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.Armed_Night,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.No_Alarm,
    )


    await reset_alarm_panel(hass, cluster, entity_id)


    cluster.listener_event(
        "cluster_command", 1, 0, [security.IasAce.ArmMode.Arm_All_Zones, "", 0]
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY


    await reset_alarm_panel(hass, cluster, entity_id)


    cluster.listener_event(
        "cluster_command", 1, 0, [security.IasAce.ArmMode.Arm_Day_Home_Only, "", 0]
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_HOME


    await reset_alarm_panel(hass, cluster, entity_id)


    cluster.listener_event(
        "cluster_command", 1, 0, [security.IasAce.ArmMode.Arm_Night_Sleep_Only, "", 0]
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_NIGHT


    cluster.listener_event(
        "cluster_command", 1, 0, [security.IasAce.ArmMode.Disarm, "", 0]
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.ARMED_NIGHT


    cluster.listener_event(
        "cluster_command", 1, 0, [security.IasAce.ArmMode.Disarm, "", 0]
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED


    cluster.listener_event(
        "cluster_command", 1, 0, [security.IasAce.ArmMode.Disarm, "4321", 0]
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.DISARMED


    cluster.listener_event("cluster_command", 1, 4, [])
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED


    await reset_alarm_panel(hass, cluster, entity_id)


    cluster.listener_event("cluster_command", 1, 3, [])
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED


    await reset_alarm_panel(hass, cluster, entity_id)


    cluster.listener_event("cluster_command", 1, 2, [])
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED


    await reset_alarm_panel(hass, cluster, entity_id)

    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_trigger",
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED
    assert cluster.client_command.call_count == 1
    assert cluster.client_command.await_count == 1
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.In_Alarm,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.Emergency_Panic,
    )


    await reset_alarm_panel(hass, cluster, entity_id)
    cluster.client_command.reset_mock()


async def reset_alarm_panel(hass: HomeAssistant, cluster: Cluster, entity_id: str):

    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_disarm",
        {ATTR_ENTITY_ID: entity_id, "code": "4321"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == AlarmControlPanelState.DISARMED
    assert cluster.client_command.call_count == 2
    assert cluster.client_command.await_count == 2
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.Panel_Disarmed,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.No_Alarm,
    )
    cluster.client_command.reset_mock()
