import asyncio
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from typing import AsyncIterator, Deque, Dict, List

ChatMessage = Dict[str, str]


class ChatConversation:
    """Bitta userning lock bilan himoyalangan suhbat oynasi."""

    def __init__(self, user_id: int, history: Deque[ChatMessage]) -> None:
        self.user_id = user_id
        self._history = history

    def get_messages(self) -> List[ChatMessage]:
        """API request uchun tarixning xavfsiz nusxasini qaytaradi."""
        return [message.copy() for message in self._history]

    def append_turn(self, user_message: str, assistant_message: str) -> None:
        """Muvaffaqiyatli savol-javob juftini sliding windowga qo'shadi."""
        self._history.append({"role": "user", "content": user_message})
        self._history.append(
            {"role": "assistant", "content": assistant_message}
        )


class _UserState:
    def __init__(self, max_messages: int) -> None:
        self.history: Deque[ChatMessage] = deque(maxlen=max_messages)
        self.lock = asyncio.Lock()
        # Lockni kutayotgan coroutine'lar ham reference hisoblanadi. Shu sabab
        # state navbat bor paytda LRU tomonidan o'chirilmaydi.
        self.references = 0


class InMemoryChatHistory:
    """User ID bo'yicha bounded, vaqtinchalik suhbat tarixini saqlaydi."""

    def __init__(self, turns_per_user: int, max_users: int) -> None:
        if turns_per_user < 1:
            raise ValueError("turns_per_user kamida 1 bo'lishi kerak.")
        if max_users < 1:
            raise ValueError("max_users kamida 1 bo'lishi kerak.")

        self._max_messages = turns_per_user * 2
        self._max_users = max_users
        self._states: "OrderedDict[int, _UserState]" = OrderedDict()
        self._registry_lock = asyncio.Lock()
        self._capacity_changed = asyncio.Condition(self._registry_lock)

    @asynccontextmanager
    async def conversation(
        self, user_id: int
    ) -> AsyncIterator[ChatConversation]:
        """Bitta userning butun requestini ketma-ket ishlash uchun lock beradi."""
        async with self._capacity_changed:
            state = self._states.get(user_id)
            while state is None:
                if len(self._states) < self._max_users:
                    state = _UserState(self._max_messages)
                    self._states[user_id] = state
                    break

                if self._evict_oldest_inactive_user():
                    continue

                # Barcha user slotlari faol. Bo'sh slot paydo bo'lguncha kutamiz.
                await self._capacity_changed.wait()
                state = self._states.get(user_id)

            state.references += 1
            self._states.move_to_end(user_id)

        acquired = False
        try:
            await state.lock.acquire()
            acquired = True
            yield ChatConversation(user_id, state.history)
        finally:
            if acquired:
                state.lock.release()
            async with self._capacity_changed:
                state.references -= 1
                if self._states.get(user_id) is state:
                    self._states.move_to_end(user_id)
                self._capacity_changed.notify_all()

    def _evict_oldest_inactive_user(self) -> bool:
        """Yangi user uchun eng eski faol bo'lmagan slotni bo'shatadi."""
        for user_id, state in list(self._states.items()):
            if state.references == 0 and not state.lock.locked():
                self._states.pop(user_id, None)
                return True
        return False
