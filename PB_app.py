import asyncio

from server import PizzaBotMain

if __name__ == "__main__":
    app = PizzaBotMain()
    asyncio.run(app.start_server())