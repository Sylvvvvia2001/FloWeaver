

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from http import HTTPStatus
import logging
import secrets
from typing import Final

from aiohttp import web
from aiohttp.abc import AbstractStreamWriter, BaseRequest

from homeassistant.components import ffmpeg
from homeassistant.components.ffmpeg import FFmpegManager
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_MAX_CONVERSIONS_PER_DEVICE: Final[int] = 2


@callback
def async_create_proxy_url(
    hass: HomeAssistant,
    device_id: str,
    media_url: str,
    media_format: str,
    rate: int | None = None,
    channels: int | None = None,
    width: int | None = None,
) -> str:

    data = hass.data[DATA_FFMPEG_PROXY]
    return data.async_create_proxy_url(
        device_id, media_url, media_format, rate, channels, width
    )


@dataclass
class FFmpegConversionInfo:


    convert_id: str
    """Unique id for media conversion."""

    media_url: str
    """Source URL of media to convert."""

    media_format: str
    """Target format for media (mp3, flac, etc.)"""

    rate: int | None
    """Target sample rate (None to keep source rate)."""

    channels: int | None
    """Target number of channels (None to keep source channels)."""

    width: int | None
    """Target sample width in bytes (None to keep source width)."""

    proc: asyncio.subprocess.Process | None = None
    """Subprocess doing ffmpeg conversion."""

    is_finished: bool = False
    """True if conversion has finished."""


@dataclass
class FFmpegProxyData:



    conversions: dict[str, list[FFmpegConversionInfo]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def async_create_proxy_url(
        self,
        device_id: str,
        media_url: str,
        media_format: str,
        rate: int | None,
        channels: int | None,
        width: int | None,
    ) -> str:



        device_conversions = [
            info for info in self.conversions[device_id] if not info.is_finished
        ]

        while len(device_conversions) >= _MAX_CONVERSIONS_PER_DEVICE:

            convert_info = device_conversions[0]
            if (convert_info.proc is not None) and (
                convert_info.proc.returncode is None
            ):
                _LOGGER.debug(
                    "Stopping existing ffmpeg process for device: %s", device_id
                )
                convert_info.proc.kill()

            device_conversions = device_conversions[1:]

        convert_id = secrets.token_urlsafe(16)
        device_conversions.append(
            FFmpegConversionInfo(
                convert_id, media_url, media_format, rate, channels, width
            )
        )
        _LOGGER.debug("Media URL allowed by proxy: %s", media_url)

        self.conversions[device_id] = device_conversions

        return f"/api/esphome/ffmpeg_proxy/{device_id}/{convert_id}.{media_format}"


class FFmpegConvertResponse(web.StreamResponse):


    def __init__(
        self,
        manager: FFmpegManager,
        convert_info: FFmpegConversionInfo,
        device_id: str,
        proxy_data: FFmpegProxyData,
        chunk_size: int = 2048,
    ) -> None:
















        super().__init__(status=200)
        self.hass = manager.hass
        self.manager = manager
        self.convert_info = convert_info
        self.device_id = device_id
        self.proxy_data = proxy_data
        self.chunk_size = chunk_size

    async def transcode(
        self, request: BaseRequest, writer: AbstractStreamWriter
    ) -> None:

        command_args = [
            "-i",
            self.convert_info.media_url,
            "-f",
            self.convert_info.media_format,
        ]

        if self.convert_info.rate is not None:

            command_args.extend(["-ar", str(self.convert_info.rate)])

        if self.convert_info.channels is not None:

            command_args.extend(["-ac", str(self.convert_info.channels)])

        if self.convert_info.width == 2:

            command_args.extend(["-sample_fmt", "s16"])


        command_args.extend(["-map_metadata", "-1", "-vn"])


        command_args.append("-nostats")


        command_args.append("pipe:")

        _LOGGER.debug("%s %s", self.manager.binary, " ".join(command_args))
        proc = await asyncio.create_subprocess_exec(
            self.manager.binary,
            *command_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            close_fds=False,
        )


        self.convert_info.proc = proc


        write_task = self.hass.async_create_background_task(
            self._write_ffmpeg_data(request, writer, proc), "ESPHome media proxy"
        )
        await write_task

    async def _write_ffmpeg_data(
        self,
        request: BaseRequest,
        writer: AbstractStreamWriter,
        proc: asyncio.subprocess.Process,
    ) -> None:
        assert proc.stdout is not None
        assert proc.stderr is not None

        stderr_task = self.hass.async_create_background_task(
            self._dump_ffmpeg_stderr(proc), "ESPHome media proxy dump stderr"
        )

        try:

            while (
                self.hass.is_running
                and (request.transport is not None)
                and (not request.transport.is_closing())
                and (chunk := await proc.stdout.read(self.chunk_size))
            ):
                await self.write(chunk)
        except asyncio.CancelledError:
            _LOGGER.debug("ffmpeg transcoding cancelled")


            if request.transport:
                request.transport.abort()
            raise
        except:
            _LOGGER.exception("Unexpected error during ffmpeg conversion")
            raise
        finally:

            self.convert_info.is_finished = True


            stderr_task.cancel()


            if proc.returncode is None:
                proc.kill()


            if request.transport and not request.transport.is_closing():
                await writer.write_eof()

    async def _dump_ffmpeg_stderr(
        self,
        proc: asyncio.subprocess.Process,
    ) -> None:
        assert proc.stdout is not None
        assert proc.stderr is not None

        while self.hass.is_running and (chunk := await proc.stderr.readline()):
            _LOGGER.debug("ffmpeg[%s] output: %s", proc.pid, chunk.decode().rstrip())


class FFmpegProxyView(HomeAssistantView):


    requires_auth = False
    url = "/api/esphome/ffmpeg_proxy/{device_id}/{filename}"
    name = "api:esphome:ffmpeg_proxy"

    def __init__(self, manager: FFmpegManager, proxy_data: FFmpegProxyData) -> None:

        self.manager = manager
        self.proxy_data = proxy_data

    async def get(
        self, request: web.Request, device_id: str, filename: str
    ) -> web.StreamResponse:

        device_conversions = self.proxy_data.conversions[device_id]
        if not device_conversions:
            return web.Response(
                body="No proxy URL for device", status=HTTPStatus.NOT_FOUND
            )


        convert_id, media_format = filename.rsplit(".")


        convert_info: FFmpegConversionInfo | None = None
        for maybe_convert_info in device_conversions:
            if (maybe_convert_info.convert_id == convert_id) and (
                maybe_convert_info.media_format == media_format
            ):
                convert_info = maybe_convert_info
                break

        if convert_info is None:
            return web.Response(body="Invalid proxy URL", status=HTTPStatus.BAD_REQUEST)




        if (convert_info.proc is not None) and (convert_info.proc.returncode is None):
            convert_info.proc.kill()
            convert_info.proc = None


        resp = FFmpegConvertResponse(
            self.manager, convert_info, device_id, self.proxy_data
        )
        writer = await resp.prepare(request)
        assert writer is not None
        await resp.transcode(request, writer)
        return resp


DATA_FFMPEG_PROXY: HassKey[FFmpegProxyData] = HassKey(f"{DOMAIN}.ffmpeg_proxy")


@callback
def async_setup(hass: HomeAssistant) -> None:

    proxy_data = FFmpegProxyData()
    hass.data[DATA_FFMPEG_PROXY] = proxy_data
    hass.http.register_view(
        FFmpegProxyView(ffmpeg.get_ffmpeg_manager(hass), proxy_data)
    )
