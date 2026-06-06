import json
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


class MemoryServer:
    """MCP-сервер для управления памятью агента с файловым JSON-хранилищем."""

    def __init__(self):
        self.mcp = FastMCP("Memory-Server")
        self.storage_path = Path("./memory_data.json")

    def _load_memory(self) -> dict:
        """Загружает память из JSON-файла."""
        if not self.storage_path.exists():
            return {}
        with open(self.storage_path, encoding="utf-8") as f:
            return json.load(f)

    def _save_memory(self, data: dict):
        """Сохраняет память в JSON-файл."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _validate_key(key: str) -> bool:
        """Валидирует ключ на безопасность.

        Запрещает path traversal, разделители путей, null-байты и control-символы.

        Args:
            key: Ключ для проверки.

        Returns:
            True если ключ безопасен, False иначе.
        """
        if not key or not isinstance(key, str):
            return False
        # Защита от path traversal и опасных символов
        if ".." in key or "/" in key or "\\" in key:
            return False
        # Null-байты
        if "\x00" in key:
            return False
        # Control characters (ASCII 0-31, кроме пробела 32)
        for char in key:
            if ord(char) < 32:
                return False
        return True


# Создаём экземпляр сервера для доступа к хранилищу из инструментов
server = MemoryServer()


@server.mcp.tool()
def save(key: str, value: Any) -> bool:
    """Сохраняет значение по ключу в память сервера.

    Args:
        key: Идентификатор для сохранения (уникальный ключ).
        value: Любое сериализуемое значение.

    Returns:
        True при успешном сохранении, False иначе.
    """
    if not server._validate_key(key):
        return False

    data = server._load_memory()
    data[key] = {
        "value": value,
        "timestamp": datetime.now().isoformat(),
    }
    server._save_memory(data)
    return True


@server.mcp.tool()
def get(key: str) -> dict | None:
    """Возвращает значение по ключу с метаданными.

    Args:
        key: Идентификатор для поиска.

    Returns:
        Словарь с полями {"key": ..., "value": ..., "timestamp": ...}
        или None если ключ не найден.
    """
    if not server._validate_key(key):
        return None

    data = server._load_memory()
    if key not in data:
        return None

    entry = data[key]
    return {
        "key": key,
        "value": entry["value"],
        "timestamp": entry["timestamp"],
    }


@server.mcp.tool()
def delete(key: str) -> bool:
    """Удаляет ключ из памяти сервера.

    Args:
        key: Идентификатор для удаления.

    Returns:
        True при успешном удалении, False если ключ не найден.
    """
    if not server._validate_key(key):
        return False

    data = server._load_memory()
    if key not in data:
        return False

    del data[key]
    server._save_memory(data)
    return True


@server.mcp.tool()
def list_keys(pattern: str = "*") -> list[str]:
    """Возвращает список всех ключей с поддержкой wildcard-паттерна.

    Args:
        pattern: Паттерн для фильтрации (поддерживает * и ?).

    Returns:
        Список совпадающих ключей.
    """
    data = server._load_memory()
    matching_keys = []
    for key in data:
        if fnmatch(key, pattern):
            matching_keys.append(key)
    return matching_keys


@server.mcp.tool()
def save_with_namespace(key: str, value: Any, namespace: str = "default") -> bool:
    """Сохраняет значение с указанием пространства имён.

    Args:
        key: Идентификатор.
        value: Значение для сохранения.
        namespace: Пространство имён (по умолчанию 'default').

    Returns:
        True при успехе, False иначе.
    """
    # Валидируем и key, и namespace отдельно
    if not server._validate_key(key) or not server._validate_key(namespace):
        return False

    # Формируем составной ключ namespace:key
    full_key = f"{namespace}:{key}"
    data = server._load_memory()
    data[full_key] = {
        "value": value,
        "timestamp": datetime.now().isoformat(),
    }
    server._save_memory(data)
    return True


@server.mcp.tool()
def get_by_namespace(namespace: str = "default") -> list[dict]:
    """Возвращает все ключи из указанного namespace.

    Args:
        namespace: Пространство имён для чтения.

    Returns:
        Список словарей с метаданными всех ключей namespace.
    """
    if not server._validate_key(namespace):
        return []

    data = server._load_memory()
    prefix = f"{namespace}:"
    results = []

    for key, entry in data.items():
        if key.startswith(prefix):
            # Возвращаем ключ без префикса namespace для удобства чтения
            short_key = key[len(prefix):]
            results.append(
                {
                    "key": short_key,
                    "value": entry["value"],
                    "timestamp": entry["timestamp"],
                }
            )

    return results


if __name__ == "__main__":
    server.mcp.run(
        transport="stdio",
        show_banner=False,
        log_level="ERROR",
    )
