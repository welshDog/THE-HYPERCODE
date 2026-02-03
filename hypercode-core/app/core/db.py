from typing import Any, Dict, List, Optional

try:
    from prisma import Prisma
    db = Prisma()
except Exception:
    class _AgentModel:
        def __init__(self):
            self._items: Dict[str, Dict[str, Any]] = {}

        async def find_first(self, where: Dict[str, Any]) -> Optional[Any]:
            for item in self._items.values():
                ok = True
                for k, v in where.items():
                    if item.get(k) != v:
                        ok = False
                        break
                if ok:
                    return _Obj(item)
            return None

        async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Optional[Any]:
            item = await self.find_unique(where=where)
            if not item:
                return None
            entry = self._items[item.id]
            entry.update({
                "name": data.get("name", entry.get("name")),
                "version": data.get("version", entry.get("version")),
                "capabilities": data.get("capabilities", entry.get("capabilities")),
                "topics": data.get("topics", entry.get("topics")),
                "healthUrl": data.get("healthUrl", entry.get("healthUrl")),
                "status": data.get("status", entry.get("status")),
                "lastHeartbeat": data.get("lastHeartbeat", entry.get("lastHeartbeat")),
            })
            return _Obj(entry)

        async def create(self, data: Dict[str, Any]) -> Any:
            self._items[data["id"]] = dict(data)
            return _Obj(self._items[data["id"]])

        async def find_unique(self, where: Dict[str, Any]) -> Optional[Any]:
            key, val = next(iter(where.items()))
            for item in self._items.values():
                if item.get(key) == val:
                    return _Obj(item)
            return None

        async def find_many(self, where: Optional[Dict[str, Any]] = None) -> List[Any]:
            if not where:
                return [_Obj(v) for v in self._items.values()]
            results = []
            for v in self._items.values():
                match = True
                for k, cond in where.items():
                    # support {status: {not: "offline"}}
                    if isinstance(cond, dict) and "not" in cond:
                        if v.get(k) == cond["not"]:
                            match = False
                            break
                    else:
                        if v.get(k) != cond:
                            match = False
                            break
                if match:
                    results.append(_Obj(v))
            return results

    class _Obj:
        def __init__(self, data: Dict[str, Any]):
            self.__dict__.update(data)

    class _InMemoryDB:
        def __init__(self):
            self.agent = _AgentModel()

        async def connect(self):
            return None

        async def disconnect(self):
            return None

    db = _InMemoryDB()
