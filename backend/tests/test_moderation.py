import asyncio
import unittest
import httpx
from backend.moderation import BullyingModerator, ModerationUnavailable
from backend.commands import dispatch
from backend.chat import ChatManager


def drain(client):
    events = []
    while not client.outbox.empty():
        events.append(client.outbox.get_nowait())
    return events


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_categories_payload_and_cache(self):
        requests = []
        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={'bully_type': 0})
        service = BullyingModerator(api_key='test-key', service_url='https://example.test/bully', transport=httpx.MockTransport(respond))
        try:
            self.assertTrue(await service.check('สวัสดี'))
            self.assertTrue(await service.check('สวัสดี'))
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0].headers['Apikey'], 'test-key')
            self.assertIn(b'text=', requests[0].content)
            for value in range(1, 7):
                self.assertFalse(service.parse({'bully_type': value}))
                self.assertFalse(service.parse({'bully_type': [value]}))
            self.assertFalse(service.parse({'bully_type': [0, 4, 6]}))
            self.assertTrue(service.parse({'bully_type': [0]}))
            for payload in [{}, {'bully_type': False}, {'bully_type': 7}, {'error': 'quota'}, [], {'bully_type': [7]}, {'bully_type': []}, {'bully_type': 0.0}]:
                with self.assertRaises(ModerationUnavailable):
                    service.parse(payload)
        finally:
            await service.close()

    async def test_failure_is_not_allowed_or_cached(self):
        for status in (401, 429, 500):
            service = BullyingModerator(api_key='test', service_url='https://example.test', transport=httpx.MockTransport(lambda r: httpx.Response(status)))
            try:
                with self.assertRaises(ModerationUnavailable):
                    await service.check('safe')
                self.assertEqual(len(service.cache), 0)
            finally:
                await service.close()

    async def test_timeout_and_missing_config(self):
        def timeout(request):
            raise httpx.ReadTimeout('timeout')
        for key in ('test', ''):
            service = BullyingModerator(api_key=key, service_url='https://example.test', transport=httpx.MockTransport(timeout))
            try:
                with self.assertRaises(ModerationUnavailable):
                    await service.check('safe')
            finally:
                await service.close()


class StubModerator:
    async def check(self, text):
        if text == 'offline':
            raise ModerationUnavailable()
        return text != 'bully'


class EnforcementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager = ChatManager()
        self.owner = self.manager.connect()
        self.guest = self.manager.connect()
        self.service = StubModerator()

    async def send(self, client, kind, **data):
        drain(client)
        await dispatch(self.manager, client, {'type': kind, 'requestId': 'test', **data}, self.service)
        return drain(client)[-1]

    async def test_create_bypass_block_and_failure(self):
        for text in ('bully', 'offline'):
            result = await self.send(self.owner, 'create', title=text, allowed=True)
            self.assertFalse(result['ok'])
            self.assertEqual(len(self.manager.rooms), 0)
        result = await self.send(self.owner, 'create', title='safe')
        self.assertTrue(result['ok'])
        self.assertEqual(len(self.manager.rooms), 1)

    async def test_message_not_delivered_without_allow(self):
        await self.send(self.owner, 'create', title='safe')
        await self.send(self.guest, 'join', roomId=self.owner.room_id)
        room = self.manager.rooms[self.owner.room_id]
        for text in ('bully', 'offline'):
            result = await self.send(self.owner, 'message', text=text)
            self.assertFalse(result['ok'])
            self.assertEqual(room.messages, [])
        result = await self.send(self.owner, 'message', text='safe')
        self.assertTrue(result['ok'])
        self.assertEqual(room.messages[-1]['text'], 'safe')

    async def test_preview_is_private_and_has_no_side_effects(self):
        drain(self.guest)
        result = await self.send(self.owner, 'moderate', scope='title', text='bully')
        self.assertTrue(result['ok'])
        self.assertFalse(result['allowed'])
        self.assertEqual(self.manager.rooms, {})
        self.assertEqual(drain(self.guest), [])

    async def test_participant_change_while_checking_prevents_delivery(self):
        await self.send(self.owner, 'create', title='safe')
        await self.send(self.guest, 'join', roomId=self.owner.room_id)
        entered, resume = asyncio.Event(), asyncio.Event()
        class Slow:
            async def check(self, text):
                entered.set()
                await resume.wait()
                return True
        task = asyncio.create_task(dispatch(self.manager, self.owner, {'type': 'message', 'text': 'old private draft', 'requestId': 'slow'}, Slow()))
        await entered.wait()
        self.manager.handle(self.guest, {'type': 'leave'})
        replacement = self.manager.connect()
        self.manager.handle(replacement, {'type': 'join', 'roomId': self.owner.room_id})
        resume.set()
        await task
        self.assertEqual(self.manager.rooms[self.owner.room_id].messages, [])
        self.assertFalse(drain(self.owner)[-1]['ok'])

    async def test_capacity_rechecked_after_moderation(self):
        from backend.chat import Room
        class Fill:
            async def check(inner, text):
                for i in range(100):
                    room = Room(title=str(i), owner_id='test')
                    self.manager.rooms[room.id] = room
                return True
        await dispatch(self.manager, self.owner, {'type': 'create', 'title': 'safe', 'requestId': 'r'}, Fill())
        self.assertIsNone(self.owner.room_id)
        self.assertEqual(len(self.manager.rooms), 100)
        self.assertFalse(drain(self.owner)[-1]['ok'])
