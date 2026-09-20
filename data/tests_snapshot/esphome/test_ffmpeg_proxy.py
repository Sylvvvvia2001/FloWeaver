

from collections.abc import Generator
from http import HTTPStatus
import io
import os
import tempfile
from unittest.mock import patch
from urllib.request import pathname2url
import wave

from aiohttp import client_exceptions
import mutagen
import pytest

from homeassistant.components import esphome
from homeassistant.components.esphome.ffmpeg_proxy import async_create_proxy_url
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.typing import ClientSessionGenerator


@pytest.fixture(name="wav_file_length")
def wav_file_length_fixture() -> int:

    return 1


@pytest.fixture(name="wav_file")
def wav_file_fixture(wav_file_length: int) -> Generator[str]:

    with tempfile.NamedTemporaryFile(mode="wb+", suffix=".wav") as temp_file:
        _write_silence(temp_file.name, wav_file_length)
        yield temp_file.name


def _write_silence(filename: str, length: int) -> None:

    with wave.open(filename, "wb") as wav_file:
        wav_file.setframerate(16000)
        wav_file.setsampwidth(2)
        wav_file.setnchannels(1)
        wav_file.writeframes(bytes(16000 * 2 * length))


async def test_async_create_proxy_url(hass: HomeAssistant) -> None:

    assert await async_setup_component(hass, "esphome", {})

    device_id = "test-device"
    convert_id = "test-id"
    media_format = "flac"
    media_url = "http://127.0.0.1/test.mp3"
    proxy_url = f"/api/esphome/ffmpeg_proxy/{device_id}/{convert_id}.{media_format}"

    with patch(
        "homeassistant.components.esphome.ffmpeg_proxy.secrets.token_urlsafe",
        return_value=convert_id,
    ):
        assert (
            async_create_proxy_url(hass, device_id, media_url, media_format)
            == proxy_url
        )


async def test_proxy_view(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    wav_file: str,
) -> None:

    device_id = "1234"

    await async_setup_component(hass, esphome.DOMAIN, {esphome.DOMAIN: {}})
    client = await hass_client()

    wav_url = pathname2url(wav_file)
    convert_id = "test-id"
    url = f"/api/esphome/ffmpeg_proxy/{device_id}/{convert_id}.mp3"


    req = await client.get(url)
    assert req.status == HTTPStatus.NOT_FOUND


    with patch(
        "homeassistant.components.esphome.ffmpeg_proxy.secrets.token_urlsafe",
        return_value=convert_id,
    ):
        assert (
            async_create_proxy_url(
                hass, device_id, wav_url, media_format="mp3", rate=22050, channels=2
            )
            == url
        )


    wrong_url = f"/api/esphome/ffmpeg_proxy/{device_id}/{convert_id}.flac"
    req = await client.get(wrong_url)
    assert req.status == HTTPStatus.BAD_REQUEST


    req = await client.get(url)
    assert req.status == HTTPStatus.OK

    mp3_data = await req.content.read()


    with io.BytesIO(mp3_data) as mp3_io:
        mp3_file = mutagen.File(mp3_io)
        assert mp3_file.info.sample_rate == 22050
        assert mp3_file.info.channels == 2


        assert round(mp3_file.info.length, 0) == 1


async def test_ffmpeg_file_doesnt_exist(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
) -> None:

    device_id = "1234"

    await async_setup_component(hass, esphome.DOMAIN, {esphome.DOMAIN: {}})
    client = await hass_client()


    url = async_create_proxy_url(hass, device_id, "missing-file", media_format="mp3")
    req = await client.get(url)



    assert req.status == HTTPStatus.OK
    mp3_data = await req.content.read()
    assert not mp3_data


async def test_lingering_process(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    wav_file: str,
) -> None:

    device_id = "1234"

    await async_setup_component(hass, esphome.DOMAIN, {esphome.DOMAIN: {}})
    client = await hass_client()

    wav_url = pathname2url(wav_file)
    url1 = async_create_proxy_url(
        hass,
        device_id,
        wav_url,
        media_format="wav",
        rate=22050,
        channels=2,
        width=2,
    )


    req1 = await client.get(url1)
    assert req1.status == HTTPStatus.OK


    await req1.content.readexactly(100)


    url2 = async_create_proxy_url(
        hass,
        device_id,
        wav_url,
        media_format="wav",
        rate=22050,
        channels=2,
        width=2,
    )

    req2 = await client.get(url2)
    assert req2.status == HTTPStatus.OK

    wav_data = await req2.content.read()


    with io.BytesIO(wav_data) as wav_io, wave.open(wav_io, "rb") as received_wav_file:





        num_frames = 0
        while chunk := received_wav_file.readframes(1024):
            num_frames += len(chunk) // (2 * 2)

        assert num_frames == 22050


@pytest.mark.parametrize("wav_file_length", [10])
async def test_request_same_url_multiple_times(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    wav_file: str,
) -> None:

    device_id = "1234"

    await async_setup_component(hass, esphome.DOMAIN, {esphome.DOMAIN: {}})
    client = await hass_client()

    wav_url = pathname2url(wav_file)
    url = async_create_proxy_url(
        hass,
        device_id,
        wav_url,
        media_format="wav",
        rate=22050,
        channels=2,
        width=2,
    )


    req1 = await client.get(url)
    assert req1.status == HTTPStatus.OK


    await req1.content.readexactly(100)


    req2 = await client.get(url)
    assert req2.status == HTTPStatus.OK

    wav_data = await req2.content.read()


    with io.BytesIO(wav_data) as wav_io, wave.open(wav_io, "rb") as received_wav_file:
        num_frames = 0
        while chunk := received_wav_file.readframes(1024):
            num_frames += len(chunk) // (2 * 2)

        assert num_frames == 22050 * 10


async def test_max_conversions_per_device(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
) -> None:

    max_conversions = 2
    device_ids = ["1234", "5678"]

    await async_setup_component(hass, esphome.DOMAIN, {esphome.DOMAIN: {}})
    client = await hass_client()

    with tempfile.TemporaryDirectory() as temp_dir:
        wav_paths = [
            os.path.join(temp_dir, f"{i}.wav") for i in range(max_conversions + 1)
        ]
        for wav_path in wav_paths:
            _write_silence(wav_path, 10)

        wav_urls = [pathname2url(p) for p in wav_paths]


        device_urls = {
            device_id: [
                async_create_proxy_url(
                    hass,
                    device_id,
                    wav_url,
                    media_format="wav",
                    rate=22050,
                    channels=2,
                    width=2,
                )
                for wav_url in wav_urls
            ]
            for device_id in device_ids
        }

        for urls in device_urls.values():

            req = await client.get(urls[0])
            assert req.status == HTTPStatus.BAD_REQUEST


            for url in urls[1:]:
                req = await client.get(url)
                assert req.status == HTTPStatus.OK


async def test_abort_on_shutdown(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
) -> None:

    device_id = "1234"

    await async_setup_component(hass, esphome.DOMAIN, {esphome.DOMAIN: {}})
    client = await hass_client()

    with tempfile.NamedTemporaryFile(mode="wb+", suffix=".wav") as temp_file:
        with wave.open(temp_file.name, "wb") as wav_file:
            wav_file.setframerate(16000)
            wav_file.setsampwidth(2)
            wav_file.setnchannels(1)
            wav_file.writeframes(bytes(16000 * 2))

        wav_url = pathname2url(temp_file.name)
        convert_id = "test-id"
        url = f"/api/esphome/ffmpeg_proxy/{device_id}/{convert_id}.mp3"

        wav_url = pathname2url(temp_file.name)
        url = async_create_proxy_url(
            hass,
            device_id,
            wav_url,
            media_format="wav",
            rate=22050,
            channels=2,
            width=2,
        )


        req = await client.get(url)
        assert req.status == HTTPStatus.OK
        initial_mp3_data = await req.content.read(4)
        assert initial_mp3_data == b"RIFF"


        await hass.async_stop()

        with pytest.raises(client_exceptions.ClientPayloadError):
            await req.content.read()
