import asyncio


class PBlogs(object):

    @classmethod
    async def logging_task(clx):
        print("Работает логгер")
        await asyncio.sleep(5)