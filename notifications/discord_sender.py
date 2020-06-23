import asyncio
import discord

from config.config import DISCORD_TOKEN


class DiscordBotAccess(discord.Client):

    def __init__(self):
        self.token = DISCORD_TOKEN
        self.prefix = '!'
        self.recievers = {
            "operator": {},
            "admin": {}
        }
        self.bot_config = {
            'message_templates': {
                'end_of_shelf_life': {
                    'text': "На объекте PIzzaBot {id} по адресу {address} осталось {N} порций продукта "
                            "{halfstaff_name} при мин остатке {min_qt}.",
                    'recievers': ('operator', 'admin')
                },
                'out_of_stock': {
                    'text': "На объекте PIzzaBot {id} по адресу {address} осталось {N} порций продукта {"
                            "halfstaff_name} при мин остатке {min_qt}.",
                    'recievers': ('operator',)
                }
            },
        }

    async def on_ready(self):
        """Event for launching client
        Get admin and operator channels dinamically"""
        print("Logged in as {0}!".format(self.user.name))
        for channel in self.get_all_channels():
            if channel.type == discord.ChannelType.text:
                name = channel.name
                if name.find("operator") == 0:
                    self.recievers["operator"][name] = channel.id
                    print("Operator channel is got")
                elif name.find("admin") == 0:
                    self.recievers["admin"][name] = channel.id
                    print("Admin channel is got")
        print("Это получатели", self.recievers)
        # await self.send("message", "dev", True)

    async def send_messages(self, message_code, data):
        """The function allows to send a message in channels\n
        Parameters:\n
        A message code : string\n
        Data : a dictionary of data for message template"""

        async def form_message(point_key, reciever, data):
            channel_key = reciever + '_' + point_key
            channel = self.get_channel(self.recievers[reciever][channel_key])
            await channel.send(self.bot_config['message_templates'][message_code]['text'].format(**data))

        for receiver in self.bot_config['message_templates'][message_code]['recievers']:
            print(f'Message is sending to {receiver}')
            await form_message('dev', receiver, data)
            print('Message is sent')

    async def send(self, client):
        print("Работает discord отправитель")
        # await client.wait_until_ready()
        while client.is_ready:
            print("приготовились отправлять")
            message_code = "out_of_stock"
            data = {'id': '1', 'address': 'here', 'halfstaff_name': 'пельмени', 'N': '3', 'min_qt': '1'}
            await self.send_messages(message_code, data)
        await asyncio.sleep(5)

    async def start_working(self, client):
        while True:
            print("Начинаем цикл отправки сообщения")
            await self.send(client)



class DiscordBotSender(object):

    def __init__(self):
        self.client = DiscordBotAccess()
        self.token = DISCORD_TOKEN

    async def start_bot_sender(self):
        loop = asyncio.get_running_loop()
        loop.create_task(self.client.start_working(self.client))
        self.client.run(self.token)

