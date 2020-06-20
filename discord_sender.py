import asyncio


class DiscordBotSender(object):

    @classmethod
    async def send_message(clx):
        print("Работает discord отправитель")
        await asyncio.sleep(5)