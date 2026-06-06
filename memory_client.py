import asyncio

from fastmcp import Client


async def main():
    # Подключение к MCP-серверу через stdio
    client = Client("python memory_server.py")

    await client.connect()

    try:
        # Сохранение данных в namespace "default"
        result = await client.call_tool(
            "save_with_namespace",
            {"key": "user_name", "value": "Алексей", "namespace": "default"},
        )
        print(f"Сохранено: {result}")

        # Чтение данных
        result = await client.call_tool(
            "get_by_namespace",
            {"namespace": "default"},
        )
        print("Данные namespace 'default':")
        for item in result:
            print(f"  {item['key']}: {item['value']}")

        # Поиск по паттерну
        keys = await client.call_tool("list_keys", {"pattern": "*name"})
        print(f"Ключи с 'name': {keys}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
