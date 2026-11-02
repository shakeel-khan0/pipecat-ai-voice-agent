"""Bounded, interruption-safe SmallWebRTC audio queue."""

from __future__ import annotations

import asyncio
from collections import deque

from pipecat.frames.frames import InterruptionFrame
from pipecat.transports.smallwebrtc import transport as webrtc_transport


_OriginalRawAudioTrack = webrtc_transport.RawAudioTrack
_OriginalSmallWebRTCClient = webrtc_transport.SmallWebRTCClient
_OriginalSmallWebRTCOutputTransport = webrtc_transport.SmallWebRTCOutputTransport


class BoundedRawAudioTrack(_OriginalRawAudioTrack):
    """RawAudioTrack with a finite producer buffer and explicit interruption clear."""

    def __init__(self, sample_rate: int, auto_silence: bool = True, max_audio_seconds=1.0):
        super().__init__(sample_rate=sample_rate, auto_silence=auto_silence)
        self._max_chunks = max(1, round(float(max_audio_seconds) * 100))
        self._space_waiters: deque[asyncio.Future] = deque()

    async def enqueue_audio_bytes(self, audio_bytes: bytes):
        if len(audio_bytes) % self._bytes_per_10ms != 0:
            raise ValueError("Audio bytes must be a multiple of 10ms size.")

        chunks = [
            audio_bytes[index : index + self._bytes_per_10ms]
            for index in range(0, len(audio_bytes), self._bytes_per_10ms)
        ]
        if len(chunks) > self._max_chunks:
            raise ValueError("One audio write exceeds the bounded WebRTC audio queue.")

        while len(self._chunk_queue) + len(chunks) > self._max_chunks:
            waiter = asyncio.get_running_loop().create_future()
            self._space_waiters.append(waiter)
            try:
                await waiter
            finally:
                if waiter in self._space_waiters:
                    self._space_waiters.remove(waiter)

        self._chunk_queue.extend((chunk, None) for chunk in chunks)

    async def recv(self):
        frame = await super().recv()
        self._wake_space_waiters()
        return frame

    def clear_audio(self):
        self._chunk_queue.clear()
        self._wake_space_waiters(all_waiters=True)

    def _wake_space_waiters(self, *, all_waiters=False):
        count = len(self._space_waiters) if all_waiters else min(1, len(self._space_waiters))
        for _ in range(count):
            waiter = self._space_waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)


class BoundedSmallWebRTCClient(_OriginalSmallWebRTCClient):
    async def write_audio_frame(self, frame):
        if self._can_send() and self._audio_output_track:
            await self._audio_output_track.enqueue_audio_bytes(frame.audio)
            return True
        return False

    def clear_output_audio(self):
        track = self._audio_output_track
        if track is not None and hasattr(track, "clear_audio"):
            track.clear_audio()

    async def _handle_peer_disconnected(self):
        self.clear_output_audio()
        await super()._handle_peer_disconnected()

    async def _handle_client_closed(self):
        self.clear_output_audio()
        await super()._handle_client_closed()


class BoundedSmallWebRTCOutputTransport(_OriginalSmallWebRTCOutputTransport):
    async def process_frame(self, frame, direction):
        if isinstance(frame, InterruptionFrame):
            self._client.clear_output_audio()
        await super().process_frame(frame, direction)

    async def _teardown(self):
        self._client.clear_output_audio()
        await super()._teardown()


def install_bounded_webrtc_audio():
    """Install the bounded classes into this process before transport construction."""
    webrtc_transport.RawAudioTrack = BoundedRawAudioTrack
    webrtc_transport.SmallWebRTCClient = BoundedSmallWebRTCClient
    webrtc_transport.SmallWebRTCOutputTransport = BoundedSmallWebRTCOutputTransport

