

import asyncio
from dataclasses import replace
from http import HTTPStatus
import io
import socket
from unittest.mock import ANY, AsyncMock, Mock, patch
import wave

from aioesphomeapi import (
    APIClient,
    MediaPlayerFormatPurpose,
    MediaPlayerInfo,
    MediaPlayerSupportedFormat,
    VoiceAssistantAnnounceFinished,
    VoiceAssistantAudioSettings,
    VoiceAssistantCommandFlag,
    VoiceAssistantEventType,
    VoiceAssistantFeature,
    VoiceAssistantTimerEventType,
)
import pytest

from homeassistant.components import (
    assist_pipeline,
    assist_satellite,
    conversation,
    tts,
)
from homeassistant.components.assist_pipeline import PipelineEvent, PipelineEventType
from homeassistant.components.assist_pipeline.pipeline import (
    KEY_ASSIST_PIPELINE,
)
from homeassistant.components.assist_satellite import (
    AssistSatelliteConfiguration,
    AssistSatelliteEntityFeature,
    AssistSatelliteWakeWord,
)


from homeassistant.components.assist_satellite.entity import AssistSatelliteState
from homeassistant.components.esphome.assist_satellite import VoiceAssistantUDPServer
from homeassistant.components.esphome.const import NO_WAKE_WORD
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, intent as intent_helper
from homeassistant.helpers.network import get_url
from homeassistant.setup import async_setup_component

from .common import get_satellite_entity
from .conftest import MockESPHomeDeviceType

from tests.components.tts.common import MockResultStream
from tests.typing import ClientSessionGenerator


@pytest.fixture
def mock_wav() -> bytes:

    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setframerate(16000)
            wav_file.setsampwidth(2)
            wav_file.setnchannels(1)
            wav_file.writeframes(b"test-wav")

        return wav_io.getvalue()


async def test_no_satellite_without_voice_assistant(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={},
    )
    await hass.async_block_till_done()


    assert get_satellite_entity(hass, mock_device.device_info.mac_address) is None


async def test_pipeline_api_audio(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    mock_wav: bytes,
) -> None:

    conversation_id = "test-conversation-id"

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
            | VoiceAssistantFeature.API_AUDIO
        },
    )
    await hass.async_block_till_done()
    dev = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mock_device.entry.unique_id)}
    )

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None



    stream_tts_audio_ready = asyncio.Event()
    original_stream_tts_audio = satellite._stream_tts_audio

    async def _stream_tts_audio(*args, **kwargs):
        await stream_tts_audio_ready.wait()
        await original_stream_tts_audio(*args, **kwargs)

    async def async_pipeline_from_audio_stream(*args, device_id, **kwargs):
        assert device_id == dev.id

        stt_stream = kwargs["stt_stream"]

        chunks = [chunk async for chunk in stt_stream]


        assert chunks == [b"test-mic"]

        event_callback = kwargs["event_callback"]


        event_callback(
            PipelineEvent(
                type="unknown-event",
                data={},
            )
        )

        mock_client.send_voice_assistant_event.assert_not_called()


        event_callback(
            PipelineEvent(
                type=PipelineEventType.ERROR,
                data={"code": "test-error-code", "message": "test-error-message"},
            )
        )

        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_ERROR,
            {"code": "test-error-code", "message": "test-error-message"},
        )


        assert satellite.state == AssistSatelliteState.IDLE

        event_callback(
            PipelineEvent(
                type=PipelineEventType.WAKE_WORD_START,
                data={
                    "entity_id": "test-wake-word-entity-id",
                    "metadata": {},
                    "timeout": 0,
                },
            )
        )

        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_WAKE_WORD_START,
            {},
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.WAKE_WORD_END, data={"wake_word_output": {}}
            )
        )

        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_ERROR,
            {"code": "no_wake_word", "message": "No wake word detected"},
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.WAKE_WORD_END,
                data={"wake_word_output": {"wake_word_phrase": "test-wake-word"}},
            )
        )

        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_WAKE_WORD_END,
            {},
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.STT_START,
                data={"engine": "test-stt-engine", "metadata": {}},
            )
        )

        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_STT_START,
            {},
        )
        assert satellite.state == AssistSatelliteState.LISTENING

        event_callback(
            PipelineEvent(
                type=PipelineEventType.STT_END,
                data={"stt_output": {"text": "test-stt-text"}},
            )
        )
        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_STT_END,
            {"text": "test-stt-text"},
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.INTENT_START,
                data={
                    "engine": "test-intent-engine",
                    "language": hass.config.language,
                    "intent_input": "test-intent-text",
                    "conversation_id": conversation_id,
                    "device_id": device_id,
                },
            )
        )

        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_INTENT_START,
            {},
        )
        assert satellite.state == AssistSatelliteState.PROCESSING

        event_callback(
            PipelineEvent(
                type=PipelineEventType.INTENT_PROGRESS,
                data={"tts_start_streaming": "1"},
            )
        )
        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_INTENT_PROGRESS,
            {"tts_start_streaming": "1"},
        )

        event_callback(
            PipelineEvent(
                type=PipelineEventType.INTENT_END,
                data={
                    "intent_output": conversation.ConversationResult(
                        response=intent_helper.IntentResponse("en"),
                        conversation_id=conversation_id,
                        continue_conversation=True,
                    ).as_dict()
                },
            )
        )
        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_INTENT_END,
            {
                "conversation_id": conversation_id,
                "continue_conversation": "1",
            },
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.TTS_START,
                data={
                    "engine": "test-stt-engine",
                    "language": hass.config.language,
                    "voice": "test-voice",
                    "tts_input": "test-tts-text",
                },
            )
        )

        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_TTS_START,
            {"text": "test-tts-text"},
        )
        assert satellite.state == AssistSatelliteState.RESPONDING


        mock_tts_result_stream = MockResultStream(hass, "wav", mock_wav)
        event_callback(
            PipelineEvent(
                type=PipelineEventType.TTS_END,
                data={
                    "tts_output": {
                        "media_id": "test-media-id",
                        "url": mock_tts_result_stream.url,
                        "token": mock_tts_result_stream.token,
                    }
                },
            )
        )
        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_TTS_END,
            {"url": get_url(hass) + mock_tts_result_stream.url},
        )

        event_callback(
            PipelineEvent(
                type=PipelineEventType.RUN_START,
                data={
                    "tts_output": {
                        "media_id": "test-media-id",
                        "url": mock_tts_result_stream.url,
                        "token": mock_tts_result_stream.token,
                    }
                },
            )
        )
        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_RUN_START,
            {"url": get_url(hass) + mock_tts_result_stream.url},
        )

        event_callback(PipelineEvent(type=PipelineEventType.RUN_END))
        assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
            VoiceAssistantEventType.VOICE_ASSISTANT_RUN_END,
            {},
        )


        stream_tts_audio_ready.set()

    pipeline_finished = asyncio.Event()
    original_handle_pipeline_finished = satellite.handle_pipeline_finished

    def handle_pipeline_finished():
        original_handle_pipeline_finished()
        pipeline_finished.set()

    tts_finished = asyncio.Event()
    original_tts_response_finished = satellite.tts_response_finished

    def tts_response_finished():
        original_tts_response_finished()
        tts_finished.set()

    with (
        patch(
            "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
            new=async_pipeline_from_audio_stream,
        ),
        patch.object(satellite, "handle_pipeline_finished", handle_pipeline_finished),
        patch.object(satellite, "_stream_tts_audio", _stream_tts_audio),
        patch.object(satellite, "tts_response_finished", tts_response_finished),
    ):

        satellite._audio_queue.put_nowait(b"leftover-data")


        mock_tts_streaming_task = Mock()
        satellite._tts_streaming_task = mock_tts_streaming_task

        async with asyncio.timeout(1):
            await satellite.handle_pipeline_start(
                conversation_id=conversation_id,
                flags=VoiceAssistantCommandFlag.USE_WAKE_WORD,
                audio_settings=VoiceAssistantAudioSettings(),
                wake_word_phrase="",
            )
            mock_tts_streaming_task.cancel.assert_called_once()
            await satellite.handle_audio(b"test-mic")
            await satellite.handle_pipeline_stop(abort=False)
            await pipeline_finished.wait()

            await tts_finished.wait()




    assert mock_client.send_voice_assistant_event.call_args_list[-2].args == (
        VoiceAssistantEventType.VOICE_ASSISTANT_TTS_STREAM_START,
        {},
    )
    assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
        VoiceAssistantEventType.VOICE_ASSISTANT_TTS_STREAM_END,
        {},
    )


    mock_client.send_voice_assistant_audio.assert_called_once_with(b"test-wav")


@pytest.mark.usefixtures("socket_enabled")
async def test_pipeline_udp_audio(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    mock_wav: bytes,
) -> None:





    conversation_id = "test-conversation-id"

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    mic_audio_event = asyncio.Event()

    async def async_pipeline_from_audio_stream(*args, device_id, **kwargs):
        stt_stream = kwargs["stt_stream"]

        chunks = []
        async for chunk in stt_stream:
            chunks.append(chunk)
            mic_audio_event.set()


        assert chunks == [b"test-mic"]

        event_callback = kwargs["event_callback"]


        event_callback(
            PipelineEvent(
                type=PipelineEventType.STT_START,
                data={"engine": "test-stt-engine", "metadata": {}},
            )
        )

        event_callback(
            PipelineEvent(
                type=PipelineEventType.STT_END,
                data={"stt_output": {"text": "test-stt-text"}},
            )
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.INTENT_START,
                data={
                    "engine": "test-intent-engine",
                    "language": hass.config.language,
                    "intent_input": "test-intent-text",
                    "conversation_id": conversation_id,
                    "device_id": device_id,
                },
            )
        )

        event_callback(
            PipelineEvent(
                type=PipelineEventType.INTENT_END,
                data={
                    "intent_output": conversation.ConversationResult(
                        response=intent_helper.IntentResponse("en"),
                        conversation_id=conversation_id,
                    ).as_dict()
                },
            )
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.TTS_START,
                data={
                    "engine": "test-stt-engine",
                    "language": hass.config.language,
                    "voice": "test-voice",
                    "tts_input": "test-tts-text",
                },
            )
        )


        mock_tts_result_stream = MockResultStream(hass, "wav", mock_wav)
        event_callback(
            PipelineEvent(
                type=PipelineEventType.TTS_END,
                data={
                    "tts_output": {
                        "media_id": "test-media-id",
                        "url": mock_tts_result_stream.url,
                        "token": mock_tts_result_stream.token,
                    }
                },
            )
        )

        event_callback(PipelineEvent(type=PipelineEventType.RUN_END))

    pipeline_finished = asyncio.Event()
    original_handle_pipeline_finished = satellite.handle_pipeline_finished

    def handle_pipeline_finished():
        original_handle_pipeline_finished()
        pipeline_finished.set()

    tts_finished = asyncio.Event()
    original_tts_response_finished = satellite.tts_response_finished

    def tts_response_finished():
        original_tts_response_finished()
        tts_finished.set()

    class TestProtocol(asyncio.DatagramProtocol):
        def __init__(self) -> None:
            self.transport = None
            self.data_received: list[bytes] = []

        def connection_made(self, transport):
            self.transport = transport

        def datagram_received(self, data: bytes, addr):
            self.data_received.append(data)

    with (
        patch(
            "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
            new=async_pipeline_from_audio_stream,
        ),
        patch.object(satellite, "handle_pipeline_finished", handle_pipeline_finished),
        patch.object(satellite, "tts_response_finished", tts_response_finished),
    ):
        async with asyncio.timeout(1):
            port = await satellite.handle_pipeline_start(
                conversation_id=conversation_id,
                flags=VoiceAssistantCommandFlag(0),
                audio_settings=VoiceAssistantAudioSettings(),
                wake_word_phrase="",
            )
            assert (port is not None) and (port > 0)

            (
                transport,
                protocol,
            ) = await asyncio.get_running_loop().create_datagram_endpoint(
                TestProtocol, remote_addr=("127.0.0.1", port)
            )
            assert isinstance(protocol, TestProtocol)


            transport.sendto(b"test-mic")


            await mic_audio_event.wait()

            await satellite.handle_pipeline_stop(abort=False)
            await pipeline_finished.wait()

            await tts_finished.wait()


    assert protocol.data_received == [b"test-wav"]


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.bind(("", port))
    sock.close()


async def test_udp_errors() -> None:

    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    protocol = VoiceAssistantUDPServer(audio_queue)

    protocol.datagram_received(b"test", ("", 0))
    assert audio_queue.qsize() == 1
    assert (await audio_queue.get()) == b"test"


    protocol.error_received(RuntimeError())
    assert audio_queue.qsize() == 1
    assert (await audio_queue.get()) is None


    assert protocol.transport is None
    protocol.send_audio_bytes(b"test")


    protocol.transport = Mock()
    protocol.remote_addr = None
    protocol.send_audio_bytes(b"test")
    protocol.transport.sendto.assert_not_called()


async def test_pipeline_media_player(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    mock_wav: bytes,
) -> None:





    conversation_id = "test-conversation-id"

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.API_AUDIO
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    async def async_pipeline_from_audio_stream(*args, device_id, **kwargs):
        stt_stream = kwargs["stt_stream"]

        async for _chunk in stt_stream:
            break

        event_callback = kwargs["event_callback"]


        event_callback(
            PipelineEvent(
                type=PipelineEventType.STT_START,
                data={"engine": "test-stt-engine", "metadata": {}},
            )
        )

        event_callback(
            PipelineEvent(
                type=PipelineEventType.STT_END,
                data={"stt_output": {"text": "test-stt-text"}},
            )
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.INTENT_START,
                data={
                    "engine": "test-intent-engine",
                    "language": hass.config.language,
                    "intent_input": "test-intent-text",
                    "conversation_id": conversation_id,
                    "device_id": device_id,
                },
            )
        )

        event_callback(
            PipelineEvent(
                type=PipelineEventType.INTENT_END,
                data={
                    "intent_output": conversation.ConversationResult(
                        response=intent_helper.IntentResponse("en"),
                        conversation_id=conversation_id,
                    ).as_dict()
                },
            )
        )


        event_callback(
            PipelineEvent(
                type=PipelineEventType.TTS_START,
                data={
                    "engine": "test-stt-engine",
                    "language": hass.config.language,
                    "voice": "test-voice",
                    "tts_input": "test-tts-text",
                },
            )
        )


        mock_tts_result_stream = MockResultStream(hass, "wav", mock_wav)
        event_callback(
            PipelineEvent(
                type=PipelineEventType.TTS_END,
                data={
                    "tts_output": {
                        "media_id": "test-media-id",
                        "url": mock_tts_result_stream.url,
                        "token": mock_tts_result_stream.token,
                    }
                },
            )
        )

        event_callback(PipelineEvent(type=PipelineEventType.RUN_END))

    pipeline_finished = asyncio.Event()
    original_handle_pipeline_finished = satellite.handle_pipeline_finished

    def handle_pipeline_finished():
        original_handle_pipeline_finished()
        pipeline_finished.set()

    tts_finished = asyncio.Event()
    original_tts_response_finished = satellite.tts_response_finished

    def tts_response_finished():
        original_tts_response_finished()
        tts_finished.set()

    with (
        patch(
            "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
            new=async_pipeline_from_audio_stream,
        ),
        patch.object(satellite, "handle_pipeline_finished", handle_pipeline_finished),
        patch.object(satellite, "tts_response_finished", tts_response_finished),
    ):
        async with asyncio.timeout(1):
            await satellite.handle_pipeline_start(
                conversation_id=conversation_id,
                flags=VoiceAssistantCommandFlag(0),
                audio_settings=VoiceAssistantAudioSettings(),
                wake_word_phrase="",
            )

            await satellite.handle_pipeline_stop(abort=False)
            await pipeline_finished.wait()

            assert satellite.state == AssistSatelliteState.RESPONDING


            await mock_device.mock_voice_assistant_handle_announcement_finished(
                VoiceAssistantAnnounceFinished(success=True)
            )
            await tts_finished.wait()

            assert satellite.state == AssistSatelliteState.IDLE


async def test_timer_events(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.TIMERS
        },
    )
    await hass.async_block_till_done()
    dev = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mock_device.entry.unique_id)}
    )

    total_seconds = (1 * 60 * 60) + (2 * 60) + 3
    await intent_helper.async_handle(
        hass,
        "test",
        intent_helper.INTENT_START_TIMER,
        {
            "name": {"value": "test timer"},
            "hours": {"value": 1},
            "minutes": {"value": 2},
            "seconds": {"value": 3},
        },
        device_id=dev.id,
    )

    mock_client.send_voice_assistant_timer_event.assert_called_with(
        VoiceAssistantTimerEventType.VOICE_ASSISTANT_TIMER_STARTED,
        ANY,
        "test timer",
        total_seconds,
        total_seconds,
        True,
    )


    mock_client.send_voice_assistant_timer_event.reset_mock()

    total_seconds += 5 * 60
    await intent_helper.async_handle(
        hass,
        "test",
        intent_helper.INTENT_INCREASE_TIMER,
        {
            "name": {"value": "test timer"},
            "minutes": {"value": 5},
        },
        device_id=dev.id,
    )

    mock_client.send_voice_assistant_timer_event.assert_called_with(
        VoiceAssistantTimerEventType.VOICE_ASSISTANT_TIMER_UPDATED,
        ANY,
        "test timer",
        total_seconds,
        ANY,
        True,
    )


async def test_unknown_timer_event(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.TIMERS
        },
    )
    await hass.async_block_till_done()
    assert mock_device.entry.unique_id is not None
    dev = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mock_device.entry.unique_id)}
    )
    assert dev is not None

    with patch(
        "homeassistant.components.esphome.assist_satellite._TIMER_EVENT_TYPES.from_hass",
        side_effect=KeyError,
    ):
        await intent_helper.async_handle(
            hass,
            "test",
            intent_helper.INTENT_START_TIMER,
            {
                "name": {"value": "test timer"},
                "hours": {"value": 1},
                "minutes": {"value": 2},
                "seconds": {"value": 3},
            },
            device_id=dev.id,
        )

        mock_client.send_voice_assistant_timer_event.assert_not_called()


async def test_streaming_tts_errors(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    mock_wav: bytes,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None


    satellite._is_running = False
    await satellite._stream_tts_audio(MockResultStream(hass, "wav", mock_wav))
    mock_client.send_voice_assistant_audio.assert_not_called()
    satellite._is_running = True


    await satellite._stream_tts_audio(MockResultStream(hass, "mp3", b""))
    mock_client.send_voice_assistant_audio.assert_not_called()


    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setframerate(48000)
            wav_file.setsampwidth(2)
            wav_file.setnchannels(1)
            wav_file.writeframes(b"test-wav")

        mock_tts_result_stream = MockResultStream(hass, "wav", wav_io.getvalue())

    await satellite._stream_tts_audio(mock_tts_result_stream)
    mock_client.send_voice_assistant_audio.assert_not_called()


    media_fetched = asyncio.Event()

    mock_tts_result_stream = MockResultStream(hass, "wav", b"")

    async def async_stream_result_slowly():
        media_fetched.set()
        await asyncio.sleep(1)
        yield mock_wav

    mock_tts_result_stream.async_stream_result = async_stream_result_slowly

    mock_client.send_voice_assistant_event.reset_mock()

    task = asyncio.create_task(satellite._stream_tts_audio(mock_tts_result_stream))
    async with asyncio.timeout(1):

        await media_fetched.wait()


    task.cancel()
    await task


    mock_client.send_voice_assistant_audio.assert_not_called()
    assert len(mock_client.send_voice_assistant_event.call_args_list) == 2


    assert mock_client.send_voice_assistant_event.call_args_list[-2].args == (
        VoiceAssistantEventType.VOICE_ASSISTANT_TTS_STREAM_START,
        {},
    )
    assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
        VoiceAssistantEventType.VOICE_ASSISTANT_TTS_STREAM_END,
        {},
    )


async def test_tts_format_from_media_player(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=[
            MediaPlayerInfo(
                object_id="mymedia_player",
                key=1,
                name="my media_player",
                supports_pause=True,
                supported_formats=[
                    MediaPlayerSupportedFormat(
                        format="flac",
                        sample_rate=48000,
                        num_channels=2,
                        purpose=MediaPlayerFormatPurpose.DEFAULT,
                        sample_bytes=2,
                    ),

                    MediaPlayerSupportedFormat(
                        format="mp3",
                        sample_rate=22050,
                        num_channels=1,
                        purpose=MediaPlayerFormatPurpose.ANNOUNCEMENT,
                        sample_bytes=2,
                    ),
                ],
            )
        ],
        user_service=[],
        states=[],
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    with patch(
        "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
    ) as mock_pipeline_from_audio_stream:
        await satellite.handle_pipeline_start(
            conversation_id="",
            flags=0,
            audio_settings=VoiceAssistantAudioSettings(),
            wake_word_phrase=None,
        )

        mock_pipeline_from_audio_stream.assert_called_once()
        kwargs = mock_pipeline_from_audio_stream.call_args_list[0].kwargs


        assert kwargs.get("tts_audio_output") == {
            tts.ATTR_PREFERRED_FORMAT: "mp3",
            tts.ATTR_PREFERRED_SAMPLE_RATE: 22050,
            tts.ATTR_PREFERRED_SAMPLE_CHANNELS: 1,
            tts.ATTR_PREFERRED_SAMPLE_BYTES: 2,
        }


async def test_tts_minimal_format_from_media_player(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=[
            MediaPlayerInfo(
                object_id="mymedia_player",
                key=1,
                name="my media_player",
                supports_pause=True,
                supported_formats=[
                    MediaPlayerSupportedFormat(
                        format="flac",
                        sample_rate=48000,
                        num_channels=2,
                        purpose=MediaPlayerFormatPurpose.DEFAULT,
                        sample_bytes=2,
                    ),

                    MediaPlayerSupportedFormat(
                        format="mp3",
                        sample_rate=0,
                        num_channels=0,
                        purpose=MediaPlayerFormatPurpose.ANNOUNCEMENT,
                        sample_bytes=0,
                    ),
                ],
            )
        ],
        user_service=[],
        states=[],
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    with patch(
        "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
    ) as mock_pipeline_from_audio_stream:
        await satellite.handle_pipeline_start(
            conversation_id="",
            flags=0,
            audio_settings=VoiceAssistantAudioSettings(),
            wake_word_phrase=None,
        )

        mock_pipeline_from_audio_stream.assert_called_once()
        kwargs = mock_pipeline_from_audio_stream.call_args_list[0].kwargs


        assert kwargs.get("tts_audio_output") == {
            tts.ATTR_PREFERRED_FORMAT: "mp3",
        }


async def test_announce_message(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
            | VoiceAssistantFeature.API_AUDIO
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    done = asyncio.Event()

    async def send_voice_assistant_announcement_await_response(
        media_id: str,
        timeout: float,
        text: str,
        start_conversation: bool,
        preannounce_media_id: str | None = None,
    ):
        assert satellite.state == AssistSatelliteState.RESPONDING
        assert media_id == "http://10.10.10.10:8123/api/tts_proxy/test-token"
        assert text == "test-text"
        assert not start_conversation
        assert not preannounce_media_id

        done.set()

    with (
        patch(
            "homeassistant.components.tts.generate_media_source_id",
            return_value="media-source://bla",
        ),
        patch(
            "homeassistant.components.tts.async_resolve_engine",
            return_value="tts.cloud_tts",
        ),
        patch(
            "homeassistant.components.tts.async_create_stream",
            return_value=MockResultStream(hass, "wav", b""),
        ),
        patch.object(
            mock_client,
            "send_voice_assistant_announcement_await_response",
            new=send_voice_assistant_announcement_await_response,
        ),
    ):
        async with asyncio.timeout(1):
            await hass.services.async_call(
                assist_satellite.DOMAIN,
                "announce",
                {
                    ATTR_ENTITY_ID: satellite.entity_id,
                    "message": "test-text",
                    "preannounce": False,
                },
                blocking=True,
            )
            await done.wait()
            assert satellite.state == AssistSatelliteState.IDLE


async def test_announce_media_id(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    device_registry: dr.DeviceRegistry,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=[
            MediaPlayerInfo(
                object_id="mymedia_player",
                key=1,
                name="my media_player",
                supports_pause=True,
                supported_formats=[
                    MediaPlayerSupportedFormat(
                        format="flac",
                        sample_rate=48000,
                        num_channels=2,
                        purpose=MediaPlayerFormatPurpose.ANNOUNCEMENT,
                        sample_bytes=2,
                    ),
                ],
            )
        ],
        user_service=[],
        states=[],
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
            | VoiceAssistantFeature.API_AUDIO
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    dev = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mock_device.entry.unique_id)}
    )

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    done = asyncio.Event()

    async def send_voice_assistant_announcement_await_response(
        media_id: str,
        timeout: float,
        text: str,
        start_conversation: bool,
        preannounce_media_id: str | None = None,
    ):
        assert satellite.state == AssistSatelliteState.RESPONDING
        assert media_id == "https://www.home-assistant.io/proxied.flac"
        assert not start_conversation
        assert not preannounce_media_id

        done.set()

    with (
        patch.object(
            mock_client,
            "send_voice_assistant_announcement_await_response",
            new=send_voice_assistant_announcement_await_response,
        ),
        patch(
            "homeassistant.components.esphome.assist_satellite.async_create_proxy_url",
            return_value="https://www.home-assistant.io/proxied.flac",
        ) as mock_async_create_proxy_url,
    ):
        async with asyncio.timeout(1):
            await hass.services.async_call(
                assist_satellite.DOMAIN,
                "announce",
                {
                    ATTR_ENTITY_ID: satellite.entity_id,
                    "media_id": "https://www.home-assistant.io/resolved.mp3",
                    "preannounce": False,
                },
                blocking=True,
            )
            await done.wait()
            assert satellite.state == AssistSatelliteState.IDLE

        mock_async_create_proxy_url.assert_called_once_with(
            hass=hass,
            device_id=dev.id,
            media_url="https://www.home-assistant.io/resolved.mp3",
            media_format="flac",
            rate=48000,
            channels=2,
            width=2,
        )


async def test_announce_message_with_preannounce(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
            | VoiceAssistantFeature.API_AUDIO
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    done = asyncio.Event()

    async def send_voice_assistant_announcement_await_response(
        media_id: str,
        timeout: float,
        text: str,
        start_conversation: bool,
        preannounce_media_id: str | None = None,
    ):
        assert satellite.state == AssistSatelliteState.RESPONDING
        assert media_id == "http://10.10.10.10:8123/api/tts_proxy/test-token"
        assert text == "test-text"
        assert not start_conversation
        assert preannounce_media_id == "test-preannounce"

        done.set()

    with (
        patch(
            "homeassistant.components.tts.generate_media_source_id",
            return_value="media-source://bla",
        ),
        patch(
            "homeassistant.components.tts.async_resolve_engine",
            return_value="tts.cloud_tts",
        ),
        patch(
            "homeassistant.components.tts.async_create_stream",
            return_value=MockResultStream(hass, "wav", b""),
        ),
        patch.object(
            mock_client,
            "send_voice_assistant_announcement_await_response",
            new=send_voice_assistant_announcement_await_response,
        ),
    ):
        async with asyncio.timeout(1):
            await hass.services.async_call(
                assist_satellite.DOMAIN,
                "announce",
                {
                    ATTR_ENTITY_ID: satellite.entity_id,
                    "message": "test-text",
                    "preannounce_media_id": "test-preannounce",
                },
                blocking=True,
            )
            await done.wait()
            assert satellite.state == AssistSatelliteState.IDLE


async def test_non_default_supported_features(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    assert not (
        satellite.supported_features & AssistSatelliteEntityFeature.START_CONVERSATION
    )
    assert not (satellite.supported_features & AssistSatelliteEntityFeature.ANNOUNCE)


async def test_start_conversation_message(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
            | VoiceAssistantFeature.API_AUDIO
            | VoiceAssistantFeature.ANNOUNCE
            | VoiceAssistantFeature.START_CONVERSATION
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    pipeline = assist_pipeline.Pipeline(
        conversation_engine="test engine",
        conversation_language="en",
        language="en",
        name="test pipeline",
        stt_engine="test stt",
        stt_language="en",
        tts_engine="test tts",
        tts_language="en",
        tts_voice=None,
        wake_word_entity=None,
        wake_word_id=None,
    )

    done = asyncio.Event()

    async def send_voice_assistant_announcement_await_response(
        media_id: str,
        timeout: float,
        text: str,
        start_conversation: bool,
        preannounce_media_id: str,
    ):
        assert satellite.state == AssistSatelliteState.RESPONDING
        assert media_id == "http://10.10.10.10:8123/api/tts_proxy/test-token"
        assert text == "test-text"
        assert start_conversation
        assert not preannounce_media_id

        done.set()

    with (
        patch(
            "homeassistant.components.tts.generate_media_source_id",
            return_value="media-source://bla",
        ),
        patch(
            "homeassistant.components.tts.async_resolve_engine",
            return_value="tts.cloud_tts",
        ),
        patch(
            "homeassistant.components.tts.async_create_stream",
            return_value=MockResultStream(hass, "wav", b""),
        ),
        patch.object(
            mock_client,
            "send_voice_assistant_announcement_await_response",
            new=send_voice_assistant_announcement_await_response,
        ),
        patch(
            "homeassistant.components.assist_satellite.entity.async_get_pipeline",
            return_value=pipeline,
        ),
    ):
        async with asyncio.timeout(1):
            await hass.services.async_call(
                assist_satellite.DOMAIN,
                "start_conversation",
                {
                    ATTR_ENTITY_ID: satellite.entity_id,
                    "start_message": "test-text",
                    "preannounce": False,
                },
                blocking=True,
            )
            await done.wait()
            assert satellite.state == AssistSatelliteState.IDLE


async def test_start_conversation_media_id(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    device_registry: dr.DeviceRegistry,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=[
            MediaPlayerInfo(
                object_id="mymedia_player",
                key=1,
                name="my media_player",
                supports_pause=True,
                supported_formats=[
                    MediaPlayerSupportedFormat(
                        format="flac",
                        sample_rate=48000,
                        num_channels=2,
                        purpose=MediaPlayerFormatPurpose.ANNOUNCEMENT,
                        sample_bytes=2,
                    ),
                ],
            )
        ],
        user_service=[],
        states=[],
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
            | VoiceAssistantFeature.API_AUDIO
            | VoiceAssistantFeature.ANNOUNCE
            | VoiceAssistantFeature.START_CONVERSATION
        },
    )
    await hass.async_block_till_done()

    dev = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mock_device.entry.unique_id)}
    )

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    pipeline = assist_pipeline.Pipeline(
        conversation_engine="test engine",
        conversation_language="en",
        language="en",
        name="test pipeline",
        stt_engine="test stt",
        stt_language="en",
        tts_engine="test tts",
        tts_language="en",
        tts_voice=None,
        wake_word_entity=None,
        wake_word_id=None,
    )

    done = asyncio.Event()

    async def send_voice_assistant_announcement_await_response(
        media_id: str,
        timeout: float,
        text: str,
        start_conversation: bool,
        preannounce_media_id: str,
    ):
        assert satellite.state == AssistSatelliteState.RESPONDING
        assert media_id == "https://www.home-assistant.io/proxied.flac"
        assert start_conversation
        assert not preannounce_media_id

        done.set()

    with (
        patch.object(
            mock_client,
            "send_voice_assistant_announcement_await_response",
            new=send_voice_assistant_announcement_await_response,
        ),
        patch(
            "homeassistant.components.esphome.assist_satellite.async_create_proxy_url",
            return_value="https://www.home-assistant.io/proxied.flac",
        ) as mock_async_create_proxy_url,
        patch(
            "homeassistant.components.assist_satellite.entity.async_get_pipeline",
            return_value=pipeline,
        ),
    ):
        async with asyncio.timeout(1):
            await hass.services.async_call(
                assist_satellite.DOMAIN,
                "start_conversation",
                {
                    ATTR_ENTITY_ID: satellite.entity_id,
                    "start_media_id": "https://www.home-assistant.io/resolved.mp3",
                    "preannounce": False,
                },
                blocking=True,
            )
            await done.wait()
            assert satellite.state == AssistSatelliteState.IDLE

        mock_async_create_proxy_url.assert_called_once_with(
            hass=hass,
            device_id=dev.id,
            media_url="https://www.home-assistant.io/resolved.mp3",
            media_format="flac",
            rate=48000,
            channels=2,
            width=2,
        )


async def test_start_conversation_message_with_preannounce(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.SPEAKER
            | VoiceAssistantFeature.API_AUDIO
            | VoiceAssistantFeature.ANNOUNCE
            | VoiceAssistantFeature.START_CONVERSATION
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    pipeline = assist_pipeline.Pipeline(
        conversation_engine="test engine",
        conversation_language="en",
        language="en",
        name="test pipeline",
        stt_engine="test stt",
        stt_language="en",
        tts_engine="test tts",
        tts_language="en",
        tts_voice=None,
        wake_word_entity=None,
        wake_word_id=None,
    )

    done = asyncio.Event()

    async def send_voice_assistant_announcement_await_response(
        media_id: str,
        timeout: float,
        text: str,
        start_conversation: bool,
        preannounce_media_id: str,
    ):
        assert satellite.state == AssistSatelliteState.RESPONDING
        assert media_id == "http://10.10.10.10:8123/api/tts_proxy/test-token"
        assert text == "test-text"
        assert start_conversation
        assert preannounce_media_id == "test-preannounce"

        done.set()

    with (
        patch(
            "homeassistant.components.tts.generate_media_source_id",
            return_value="media-source://bla",
        ),
        patch(
            "homeassistant.components.tts.async_resolve_engine",
            return_value="tts.cloud_tts",
        ),
        patch(
            "homeassistant.components.tts.async_create_stream",
            return_value=MockResultStream(hass, "wav", b""),
        ),
        patch.object(
            mock_client,
            "send_voice_assistant_announcement_await_response",
            new=send_voice_assistant_announcement_await_response,
        ),
        patch(
            "homeassistant.components.assist_satellite.entity.async_get_pipeline",
            return_value=pipeline,
        ),
    ):
        async with asyncio.timeout(1):
            await hass.services.async_call(
                assist_satellite.DOMAIN,
                "start_conversation",
                {
                    ATTR_ENTITY_ID: satellite.entity_id,
                    "start_message": "test-text",
                    "preannounce_media_id": "test-preannounce",
                },
                blocking=True,
            )
            await done.wait()
            assert satellite.state == AssistSatelliteState.IDLE


async def test_satellite_unloaded_on_disconnect(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    state = hass.states.get(satellite.entity_id)
    assert state is not None
    assert state.state != STATE_UNAVAILABLE


    await mock_device.mock_disconnect(True)

    state = hass.states.get(satellite.entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_pipeline_abort(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.API_AUDIO
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None

    chunks = []
    chunk_received = asyncio.Event()
    pipeline_aborted = asyncio.Event()

    async def async_pipeline_from_audio_stream(*args, **kwargs):
        stt_stream = kwargs["stt_stream"]

        try:
            async for chunk in stt_stream:
                chunks.append(chunk)
                chunk_received.set()
        except asyncio.CancelledError:

            pipeline_aborted.set()
            raise

    pipeline_finished = asyncio.Event()
    original_handle_pipeline_finished = satellite.handle_pipeline_finished

    def handle_pipeline_finished():
        original_handle_pipeline_finished()
        pipeline_finished.set()

    with (
        patch(
            "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
            new=async_pipeline_from_audio_stream,
        ),
        patch.object(satellite, "handle_pipeline_finished", handle_pipeline_finished),
    ):
        async with asyncio.timeout(1):
            await satellite.handle_pipeline_start(
                conversation_id="",
                flags=VoiceAssistantCommandFlag(0),
                audio_settings=VoiceAssistantAudioSettings(),
                wake_word_phrase="",
            )

            await satellite.handle_audio(b"before-abort")
            await chunk_received.wait()


            await satellite.handle_pipeline_stop(abort=True)
            await pipeline_aborted.wait()


            await satellite.handle_audio(b"after-abort")
            await pipeline_finished.wait()


            assert chunks == [b"before-abort"]


async def test_get_set_configuration(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    expected_config = AssistSatelliteConfiguration(
        available_wake_words=[
            AssistSatelliteWakeWord("1234", "okay nabu", ["en"]),
            AssistSatelliteWakeWord("5678", "hey jarvis", ["en"]),
        ],
        active_wake_words=["1234"],
        max_active_wake_words=2,
    )
    mock_client.get_voice_assistant_configuration.return_value = expected_config

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None


    actual_config = satellite.async_get_configuration()
    assert actual_config == expected_config

    updated_config = replace(actual_config, active_wake_words=["5678"])
    mock_client.get_voice_assistant_configuration.return_value = updated_config


    await satellite.async_set_configuration(updated_config)


    mock_client.set_voice_assistant_configuration.assert_called_once_with(
        active_wake_words=["5678"]
    )


    assert satellite.async_get_configuration() == updated_config


async def test_intent_progress_optimization(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None


    mock_client.send_voice_assistant_event.reset_mock()
    satellite.on_pipeline_event(
        PipelineEvent(
            type=PipelineEventType.INTENT_PROGRESS,
            data={"some_other_key": "value"},
        )
    )
    mock_client.send_voice_assistant_event.assert_not_called()


    satellite.on_pipeline_event(
        PipelineEvent(
            type=PipelineEventType.INTENT_PROGRESS,
            data={"tts_start_streaming": False},
        )
    )
    mock_client.send_voice_assistant_event.assert_not_called()


    satellite.on_pipeline_event(
        PipelineEvent(
            type=PipelineEventType.INTENT_PROGRESS,
            data={"tts_start_streaming": True},
        )
    )
    assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
        VoiceAssistantEventType.VOICE_ASSISTANT_INTENT_PROGRESS,
        {"tts_start_streaming": "1"},
    )


    mock_client.send_voice_assistant_event.reset_mock()
    satellite.on_pipeline_event(
        PipelineEvent(
            type=PipelineEventType.INTENT_PROGRESS,
            data={"tts_start_streaming": "1"},
        )
    )
    assert mock_client.send_voice_assistant_event.call_args_list[-1].args == (
        VoiceAssistantEventType.VOICE_ASSISTANT_INTENT_PROGRESS,
        {"tts_start_streaming": "1"},
    )


    mock_client.send_voice_assistant_event.reset_mock()
    satellite.on_pipeline_event(
        PipelineEvent(
            type=PipelineEventType.INTENT_PROGRESS,
            data=None,
        )
    )
    mock_client.send_voice_assistant_event.assert_not_called()


async def test_wake_word_select(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    device_config = AssistSatelliteConfiguration(
        available_wake_words=[
            AssistSatelliteWakeWord("okay_nabu", "Okay Nabu", ["en"]),
            AssistSatelliteWakeWord("hey_jarvis", "Hey Jarvis", ["en"]),
            AssistSatelliteWakeWord("hey_mycroft", "Hey Mycroft", ["en"]),
        ],
        active_wake_words=["hey_jarvis"],
        max_active_wake_words=2,
    )
    mock_client.get_voice_assistant_configuration.return_value = device_config


    configuration_set = asyncio.Event()

    async def wrapper(*args, **kwargs):

        device_config.active_wake_words = kwargs["active_wake_words"]
        configuration_set.set()

    mock_client.set_voice_assistant_configuration = AsyncMock(side_effect=wrapper)

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None
    assert satellite.async_get_configuration().active_wake_words == ["hey_jarvis"]


    state = hass.states.get("select.test_wake_word")
    assert state is not None
    assert state.state == "Hey Jarvis"


    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word", "option": "Okay Nabu"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get("select.test_wake_word")
    assert state is not None
    assert state.state == "Okay Nabu"


    async with asyncio.timeout(1):
        await configuration_set.wait()


    assert satellite.async_get_configuration().active_wake_words == ["okay_nabu"]


    state = hass.states.get("select.test_wake_word_2")
    assert state is not None
    assert state.state == NO_WAKE_WORD


    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word_2", "option": "Hey Jarvis"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get("select.test_wake_word_2")
    assert state is not None
    assert state.state == "Hey Jarvis"


    async with asyncio.timeout(1):
        await configuration_set.wait()


    assert set(satellite.async_get_configuration().active_wake_words) == {
        "okay_nabu",
        "hey_jarvis",
    }


    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word_2", "option": NO_WAKE_WORD},
        blocking=True,
    )
    await hass.async_block_till_done()

    async with asyncio.timeout(1):
        await configuration_set.wait()


    assert satellite.async_get_configuration().active_wake_words == ["okay_nabu"]


    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word", "option": NO_WAKE_WORD},
        blocking=True,
    )
    await hass.async_block_till_done()

    async with asyncio.timeout(1):
        await configuration_set.wait()


    assert not satellite.async_get_configuration().active_wake_words


async def test_secondary_pipeline(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    assert await async_setup_component(hass, "assist_pipeline", {})
    pipeline_data = hass.data[KEY_ASSIST_PIPELINE]
    pipeline_id_to_name: dict[str, str] = {}
    for pipeline_name in ("Primary Pipeline", "Secondary Pipeline"):
        pipeline = await pipeline_data.pipeline_store.async_create_item(
            {
                "name": pipeline_name,
                "language": "en-US",
                "conversation_engine": None,
                "conversation_language": "en-US",
                "tts_engine": None,
                "tts_language": None,
                "tts_voice": None,
                "stt_engine": None,
                "stt_language": None,
                "wake_word_entity": None,
                "wake_word_id": None,
            }
        )
        pipeline_id_to_name[pipeline.id] = pipeline_name

    device_config = AssistSatelliteConfiguration(
        available_wake_words=[
            AssistSatelliteWakeWord("okay_nabu", "Okay Nabu", ["en"]),
            AssistSatelliteWakeWord("hey_jarvis", "Hey Jarvis", ["en"]),
            AssistSatelliteWakeWord("hey_mycroft", "Hey Mycroft", ["en"]),
        ],
        active_wake_words=["hey_jarvis"],
        max_active_wake_words=2,
    )
    mock_client.get_voice_assistant_configuration.return_value = device_config


    configuration_set = asyncio.Event()

    async def wrapper(*args, **kwargs):

        device_config.active_wake_words = kwargs["active_wake_words"]
        configuration_set.set()

    mock_client.set_voice_assistant_configuration = AsyncMock(side_effect=wrapper)

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None


    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word", "option": "Okay Nabu"},
        blocking=True,
    )
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_assistant", "option": "Primary Pipeline"},
        blocking=True,
    )
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word_2", "option": "Hey Jarvis"},
        blocking=True,
    )
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: "select.test_assistant_2",
            "option": "Secondary Pipeline",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    async def get_pipeline(wake_word_phrase):
        with patch(
            "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
        ) as mock_pipeline_from_audio_stream:
            await satellite.handle_pipeline_start(
                conversation_id="",
                flags=0,
                audio_settings=VoiceAssistantAudioSettings(),
                wake_word_phrase=wake_word_phrase,
            )

            mock_pipeline_from_audio_stream.assert_called_once()
            kwargs = mock_pipeline_from_audio_stream.call_args_list[0].kwargs
            return pipeline_id_to_name[kwargs["pipeline_id"]]


    for wake_word_phrase in (None, "Okay Nabu"):
        assert (await get_pipeline(wake_word_phrase)) == "Primary Pipeline"


    assert (await get_pipeline("Hey Jarvis")) == "Secondary Pipeline"


    assert (await get_pipeline(None)) == "Primary Pipeline"


@pytest.mark.timeout(5)
async def test_pipeline_start_missing_wake_word_entity_state(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:





    assert await async_setup_component(hass, "assist_pipeline", {})
    pipeline_data = hass.data[KEY_ASSIST_PIPELINE]
    pipeline_id_to_name: dict[str, str] = {}
    for pipeline_name in ("Primary Pipeline", "Secondary Pipeline"):
        pipeline = await pipeline_data.pipeline_store.async_create_item(
            {
                "name": pipeline_name,
                "language": "en-US",
                "conversation_engine": None,
                "conversation_language": "en-US",
                "tts_engine": None,
                "tts_language": None,
                "tts_voice": None,
                "stt_engine": None,
                "stt_language": None,
                "wake_word_entity": None,
                "wake_word_id": None,
            }
        )
        pipeline_id_to_name[pipeline.id] = pipeline_name

    device_config = AssistSatelliteConfiguration(
        available_wake_words=[
            AssistSatelliteWakeWord("okay_nabu", "Okay Nabu", ["en"]),
            AssistSatelliteWakeWord("hey_jarvis", "Hey Jarvis", ["en"]),
        ],
        active_wake_words=["hey_jarvis"],
        max_active_wake_words=2,
    )
    mock_client.get_voice_assistant_configuration.return_value = device_config

    configuration_set = asyncio.Event()

    async def wrapper(*args, **kwargs):
        device_config.active_wake_words = kwargs["active_wake_words"]
        configuration_set.set()

    mock_client.set_voice_assistant_configuration = AsyncMock(side_effect=wrapper)

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None


    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word", "option": "Okay Nabu"},
        blocking=True,
    )
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_assistant", "option": "Primary Pipeline"},
        blocking=True,
    )
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_wake_word_2", "option": "Hey Jarvis"},
        blocking=True,
    )
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: "select.test_assistant_2",
            "option": "Secondary Pipeline",
        },
        blocking=True,
    )
    await hass.async_block_till_done()



    hass.states.async_remove("select.test_wake_word")

    async def get_pipeline(wake_word_phrase):
        with patch(
            "homeassistant.components.assist_satellite.entity.async_pipeline_from_audio_stream",
        ) as mock_pipeline_from_audio_stream:
            await satellite.handle_pipeline_start(
                conversation_id="",
                flags=0,
                audio_settings=VoiceAssistantAudioSettings(),
                wake_word_phrase=wake_word_phrase,
            )

            mock_pipeline_from_audio_stream.assert_called_once()
            kwargs = mock_pipeline_from_audio_stream.call_args_list[0].kwargs
            return pipeline_id_to_name[kwargs["pipeline_id"]]



    assert (await get_pipeline("Hey Jarvis")) == "Secondary Pipeline"



    assert (await get_pipeline("Okay Nabu")) == "Primary Pipeline"


    assert (await get_pipeline(None)) == "Primary Pipeline"


async def test_custom_wake_words(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    hass_client: ClientSessionGenerator,
) -> None:






    http_client = await hass_client()
    expected_config = AssistSatelliteConfiguration(
        available_wake_words=[
            AssistSatelliteWakeWord("1234", "okay nabu", ["en"]),
        ],
        active_wake_words=["1234"],
        max_active_wake_words=1,
    )
    gvac = mock_client.get_voice_assistant_configuration
    gvac.return_value = expected_config

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        device_info={
            "voice_assistant_feature_flags": VoiceAssistantFeature.VOICE_ASSISTANT
            | VoiceAssistantFeature.ANNOUNCE
        },
    )
    await hass.async_block_till_done()

    satellite = get_satellite_entity(hass, mock_device.device_info.mac_address)
    assert satellite is not None


    gvac.assert_called_once()
    external_wake_words = gvac.call_args_list[0].kwargs["external_wake_words"]
    assert len(external_wake_words) == 2

    assert {external_wake_words[0].id, external_wake_words[1].id} == {
        "hey_home_assistant",
        "choo_choo_homie",
    }


    for eww in external_wake_words:
        if eww.id == "hey_home_assistant":
            assert eww.wake_word == "Hey Home Assistant"
        else:
            assert eww.wake_word == "Choo Choo Homie"

        assert eww.model_type == "micro"
        assert eww.model_size == 4
        assert (
            eww.model_hash
            == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        )
        assert eww.trained_languages == ["en"]


        config_url = eww.url[eww.url.find("/api") :]
        req = await http_client.get(config_url)
        assert req.status == HTTPStatus.OK
        config_dict = await req.json()


        model = config_dict["model"]
        model_url = config_url[: config_url.rfind("/")] + f"/{model}"
        req = await http_client.get(model_url)
        assert req.status == HTTPStatus.OK


    req = await http_client.get("/api/esphome/wake_words/wrong_wake_word.json")
    assert req.status == HTTPStatus.NOT_FOUND
