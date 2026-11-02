import asyncio
import unittest

from bounded_webrtc_audio import BoundedRawAudioTrack, BoundedSmallWebRTCClient


def pcm_chunk(track, value):
    return int(value).to_bytes(2, "little", signed=True) * track._samples_per_10ms


class FakeConnection:
    def event_handler(self, _event_name):
        return lambda handler: handler


class BoundedWebRTCAudioTests(unittest.IsolatedAsyncioTestCase):
    async def test_queue_is_ordered_and_only_blocks_at_capacity(self):
        track = BoundedRawAudioTrack(24000, max_audio_seconds=0.02)
        first = pcm_chunk(track, 1)
        second = pcm_chunk(track, 2)
        third = pcm_chunk(track, 3)

        await track.enqueue_audio_bytes(first + second)
        blocked = asyncio.create_task(track.enqueue_audio_bytes(third))
        await asyncio.sleep(0)
        self.assertFalse(blocked.done())
        self.assertEqual(len(track._chunk_queue), 2)

        frame = await track.recv()
        await asyncio.wait_for(blocked, timeout=0.1)
        self.assertEqual(frame.to_ndarray().tobytes(), first)
        self.assertEqual([chunk for chunk, _ in track._chunk_queue], [second, third])

    async def test_interruption_clear_discards_stale_audio_and_releases_producer(self):
        track = BoundedRawAudioTrack(24000, max_audio_seconds=0.01)
        stale = pcm_chunk(track, 7)
        fresh = pcm_chunk(track, 8)

        await track.enqueue_audio_bytes(stale)
        blocked = asyncio.create_task(track.enqueue_audio_bytes(fresh))
        await asyncio.sleep(0)
        self.assertFalse(blocked.done())

        track.clear_audio()
        await asyncio.wait_for(blocked, timeout=0.1)
        self.assertEqual([chunk for chunk, _ in track._chunk_queue], [fresh])

    async def test_cancelled_blocked_producer_is_removed_cleanly(self):
        track = BoundedRawAudioTrack(24000, max_audio_seconds=0.01)
        await track.enqueue_audio_bytes(pcm_chunk(track, 1))
        blocked = asyncio.create_task(track.enqueue_audio_bytes(pcm_chunk(track, 2)))
        await asyncio.sleep(0)

        blocked.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await blocked
        self.assertFalse(track._space_waiters)

    async def test_disconnect_clears_queue_for_reconnect_cleanup(self):
        client = BoundedSmallWebRTCClient(FakeConnection(), callbacks=None)
        track = BoundedRawAudioTrack(24000, max_audio_seconds=0.02)
        await track.enqueue_audio_bytes(pcm_chunk(track, 9))
        client._audio_output_track = track

        await client._handle_peer_disconnected()

        self.assertFalse(track._chunk_queue)
        self.assertIsNone(client._audio_output_track)
