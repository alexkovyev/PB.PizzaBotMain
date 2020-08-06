import asyncio

from kbs.ssc_utils.server import Server


if __name__ == "__main__":
    app = Server()
    asyncio.run(app.start_server())
