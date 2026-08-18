from telethon import TelegramClient

api_id = int(input("API ID: "))
api_hash = input("API Hash: ")

client = TelegramClient("test_session", api_id, api_hash)

async def main():
    link = "https://t.me/shachiburi_one_piece"

    try:
        channel = await client.get_entity(link)

        print("\n✅ Канал найден!")
        print("Название:", channel.title)
        print("ID:", channel.id)

    except Exception as e:
        print("\n❌ Не удалось получить канал:")
        print(type(e).__name__, e)

with client:
    client.loop.run_until_complete(main())