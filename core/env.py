"""قراءة الإعدادات من البيئة ثم من ملف .env.

الفرق عن python-decouple: المتغير الفارغ في البيئة يُعامل كغير مضبوط.
هذا يسمح لـ docker-compose بتمرير ${VAR:-} دون أن يطمس قيمة موجودة في .env.
"""

import os
from pathlib import Path

from decouple import RepositoryEnv, UndefinedValueError

_UNDEFINED = object()
_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f", ""}


class EnvConfig:
    def __init__(self, env_file):
        path = Path(env_file)
        self._repo = RepositoryEnv(str(path)) if path.is_file() else None

    def _raw(self, name):
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
        if self._repo is not None and name in self._repo:
            value = self._repo[name]
            if value != "":
                return value
        return _UNDEFINED

    def __call__(self, name, default=_UNDEFINED, cast=None):
        value = self._raw(name)
        if value is _UNDEFINED:
            if default is _UNDEFINED:
                raise UndefinedValueError(f"{name} غير مضبوط في البيئة ولا في .env")
            value = default
        if cast is bool:
            if isinstance(value, bool):
                return value
            lowered = str(value).strip().lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
            raise ValueError(f"قيمة منطقية غير صالحة لـ {name}: {value!r}")
        if cast is not None:
            return cast(value)
        return value
