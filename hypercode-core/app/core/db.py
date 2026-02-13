from typing import Any, Dict, List, Optional

try:
    from prisma import Prisma
    db = Prisma()
except Exception:  # pragma: no cover
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

    class _MemoryModel:
        def __init__(self):
            self._items: Dict[str, Dict[str, Any]] = {}

        async def create(self, data: Dict[str, Any]) -> Any:
            import uuid, datetime
            mid = data.get("id") or str(uuid.uuid4())
            now = datetime.datetime.now(datetime.UTC)
            entry = dict(data)
            entry["id"] = mid
            entry["createdAt"] = entry.get("createdAt") or now
            entry["updatedAt"] = entry.get("updatedAt") or now
            self._items[mid] = entry
            return _Obj(self._items[mid])

        async def find_unique(self, where: Dict[str, Any]) -> Optional[Any]:
            key, val = next(iter(where.items()))
            for item in self._items.values():
                if item.get(key) == val:
                    return _Obj(item)
            return None

        async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Optional[Any]:
            item = await self.find_unique(where=where)
            if not item:
                return None
            import datetime
            entry = self._items[item.id]
            for k, v in data.items():
                entry[k] = v
            entry["updatedAt"] = datetime.datetime.now(datetime.UTC)
            return _Obj(entry)

        async def delete(self, where: Dict[str, Any]) -> Optional[Any]:
            key, val = next(iter(where.items()))
            target = None
            for mid, item in self._items.items():
                if item.get(key) == val:
                    target = mid
                    break
            if target:
                obj = _Obj(self._items[target])
                del self._items[target]
                return obj
            return None

        async def find_many(self, where: Optional[Dict[str, Any]] = None, take: Optional[int] = None, skip: int = 0, order: Optional[Dict[str, Any]] = None) -> List[Any]:
            items = list(self._items.values())
            if where:
                def matches(entry):
                    for k, cond in where.items():
                        if k == "OR" and isinstance(cond, list):
                            ok_any = False
                            for sub in cond:
                                # content contains insensitive
                                if "content" in sub:
                                    text = sub["content"].get("contains")
                                    mode = sub["content"].get("mode")
                                    if text:
                                        val = (entry.get("content") or "")
                                        if mode == "insensitive":
                                            if text.lower() in val.lower():
                                                ok_any = True
                                        else:
                                            if text in val:
                                                ok_any = True
                                if "keywords" in sub and isinstance(sub["keywords"], dict) and "has" in sub["keywords"]:
                                    needle = sub["keywords"]["has"]
                                    ks = entry.get("keywords") or []
                                    if needle in ks:
                                        ok_any = True
                            if not ok_any:
                                return False
                        else:
                            v = entry.get(k)
                            if isinstance(cond, dict) and "lt" in cond:
                                import datetime
                                if not isinstance(v, datetime.datetime):
                                    return False
                                if not (v < cond["lt"]):
                                    return False
                            else:
                                if v != cond:
                                    return False
                    return True
                items = [e for e in items if matches(e)]
            if order and "createdAt" in order:
                reverse = order["createdAt"] == "desc"
                items.sort(key=lambda x: x.get("createdAt"), reverse=reverse)
            if skip:
                items = items[skip:]
            if take is not None:
                items = items[:take]
            return [_Obj(v) for v in items]

        async def delete_many(self, where: Dict[str, Any]) -> int:
            if "expiresAt" in where and isinstance(where["expiresAt"], dict) and "lt" in where["expiresAt"]:
                import datetime
                threshold = where["expiresAt"]["lt"]
                to_delete = [mid for mid, v in self._items.items() if isinstance(v.get("expiresAt"), datetime.datetime) and v["expiresAt"] < threshold]
                for mid in to_delete:
                    del self._items[mid]
                return len(to_delete)
            return 0

    class _MissionModel:
        def __init__(self):
            self._items: Dict[str, Dict[str, Any]] = {}

        async def create(self, data: Dict[str, Any]) -> Any:
            import uuid, datetime
            mid = data.get("id") or str(uuid.uuid4())
            now = datetime.datetime.now(datetime.UTC)
            entry = dict(data)
            entry["id"] = mid
            entry["createdAt"] = entry.get("createdAt") or now
            entry["updatedAt"] = entry.get("updatedAt") or now
            self._items[mid] = entry
            return _Obj(self._items[mid])

        async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Optional[Any]:
            item = await self.find_unique(where=where)
            if not item:
                return None
            import datetime
            entry = self._items[item.id]
            for k, v in data.items():
                entry[k] = v
            entry["updatedAt"] = datetime.datetime.now(datetime.UTC)
            return _Obj(entry)

        async def find_unique(self, where: Dict[str, Any]) -> Optional[Any]:
            key, val = next(iter(where.items()))
            for item in self._items.values():
                if item.get(key) == val:
                    return _Obj(item)
            return None

        async def find_many(self, where: Optional[Dict[str, Any]] = None, take: Optional[int] = None, skip: int = 0, order: Optional[Dict[str, Any]] = None) -> List[Any]:
            items = list(self._items.values())
            if where:
                def matches(entry):
                    for k, cond in where.items():
                        v = entry.get(k)
                        if isinstance(cond, dict) and "not" in cond:
                            if v == cond["not"]:
                                return False
                        else:
                            if v != cond:
                                return False
                    return True
                items = [e for e in items if matches(e)]
            if order and "createdAt" in order:
                reverse = order["createdAt"] == "desc"
                items.sort(key=lambda x: x.get("createdAt"), reverse=reverse)
            if skip:
                items = items[skip:]
            if take is not None:
                items = items[:take]
            return [_Obj(v) for v in items]

    class _AuditLogModel:
        def __init__(self):
            self._items: Dict[str, Dict[str, Any]] = {}

        async def create(self, data: Dict[str, Any]) -> Any:
            import uuid, datetime
            aid = data.get("id") or str(uuid.uuid4())
            now = datetime.datetime.now(datetime.UTC)
            entry = dict(data)
            entry["id"] = aid
            entry["timestamp"] = entry.get("timestamp") or now
            self._items[aid] = entry
            return _Obj(self._items[aid])

        async def find_many(self, where: Optional[Dict[str, Any]] = None, order: Optional[Dict[str, Any]] = None, take: Optional[int] = None, skip: int = 0) -> List[Any]:
            items = list(self._items.values())
            if where:
                def matches(entry):
                    for k, v in where.items():
                        if entry.get(k) != v:
                            return False
                    return True
                items = [e for e in items if matches(e)]
            if order and "timestamp" in order:
                reverse = order["timestamp"] == "desc"
                items.sort(key=lambda x: x.get("timestamp"), reverse=reverse)
            if skip:
                items = items[skip:]
            if take is not None:
                items = items[:take]
            return [_Obj(v) for v in items]

    class _TokenUsageModel:
        def __init__(self):
            self._items: Dict[str, Dict[str, Any]] = {}

        async def create(self, data: Dict[str, Any]) -> Any:
            import uuid, datetime
            tid = data.get("id") or str(uuid.uuid4())
            now = datetime.datetime.now(datetime.UTC)
            entry = dict(data)
            entry["id"] = tid
            entry["timestamp"] = entry.get("timestamp") or now
            self._items[tid] = entry
            return _Obj(self._items[tid])

        async def find_many(self, where: Optional[Dict[str, Any]] = None) -> List[Any]:
            items = list(self._items.values())
            return [_Obj(v) for v in items]

    class _Obj:
        def __init__(self, data: Dict[str, Any]):
            self.__dict__.update(data)

    class _InMemoryDB:
        def __init__(self):
            self.agent = _AgentModel()
            self.memory = _MemoryModel()
            self.mission = _MissionModel()
            self.auditlog = _AuditLogModel()
            self.tokenusage = _TokenUsageModel()

        async def connect(self):
            return None

        async def disconnect(self):
            return None

    db = _InMemoryDB()
