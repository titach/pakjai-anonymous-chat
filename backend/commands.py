"""Validate drafts and enforce moderation before committing room/message actions."""
import time

if __package__:
    from .moderation import ModerationUnavailable
else:
    from moderation import ModerationUnavailable

UNAVAILABLE = 'ระบบตรวจข้อความไม่พร้อมใช้งาน กรุณาลองใหม่ ข้อความของคุณยังไม่ถูกส่ง'
BLOCKED = 'ข้อความนี้อาจมีลักษณะการรังแก กรุณาปรับข้อความก่อนใช้งาน'


async def dispatch(manager, client, data, moderator):
    if not isinstance(data, dict) or data.get('type') not in ('moderate', 'create', 'message'):
        manager.handle(client, data)
        return
    kind = data['type']
    request_id = data.get('requestId')
    if not isinstance(request_id, str) or len(request_id) > 80:
        request_id = None

    def result(ok, message='', **extra):
        manager.emit(client, {'type': 'result', 'requestId': request_id,
                             'ok': ok, 'message': message, **extra})
        if not ok and request_id is None:
            manager.error(client, message)

    now = time.monotonic()
    while client.moderations and now - client.moderations[0] >= 10:
        client.moderations.popleft()
    if len(client.moderations) >= 20:
        return result(False, 'ตรวจข้อความถี่เกินไป กรุณารอสักครู่แล้วลองใหม่')
    client.moderations.append(now)
    scope = data.get('scope') if kind == 'moderate' else ('title' if kind == 'create' else 'message')
    text = data.get('title') if kind == 'create' else data.get('text')
    maximum = 80 if scope == 'title' else 1000
    if scope not in ('title', 'message') or not isinstance(text, str) or not 1 <= len(text.strip()) <= maximum:
        return result(False, f'กรุณาใส่ข้อความ 1–{maximum} ตัวอักษร')
    text = text.strip()
    room = manager.rooms.get(client.room_id)
    # Capture participant identity before yielding to an external service.
    membership = (room.id, room.guest_id) if room else None
    if kind == 'create' and client.room_id:
        return result(False, 'คุณอยู่ในห้องแล้ว กรุณาออกจากห้องเดิมก่อน')
    if kind == 'message' and (room is None or room.guest_id is None):
        return result(False, 'กรุณารอผู้เข้าร่วมก่อนส่งข้อความ')
    try:
        allowed = await moderator.check(text)
    except ModerationUnavailable:
        return result(False, UNAVAILABLE)
    if client.id not in manager.clients or client.stopped.is_set():
        return
    if kind == 'moderate':
        return result(True, '' if allowed else BLOCKED, allowed=allowed)
    if not allowed:
        return result(False, BLOCKED, allowed=False)
    current = manager.rooms.get(client.room_id)
    if kind == 'message' and (current is None or (current.id, current.guest_id) != membership):
        return result(False, 'ผู้เข้าร่วมเปลี่ยนไปแล้ว กรุณาตรวจสอบห้องก่อนส่งอีกครั้ง')
    # Re-run all synchronous limits/membership checks after awaiting the API.
    committed = manager.handle(client, data)
    result(bool(committed), '' if committed else 'ทำรายการไม่สำเร็จ กรุณาตรวจสอบสถานะห้องแล้วลองใหม่')
