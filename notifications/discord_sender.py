import discord

from config.config import DISCORD_TOKEN, DISCORD_TEMPLATES


class DiscordBotAccess(discord.Client):

    def __init__(self):
        super().__init__()
        self.token = DISCORD_TOKEN
        self.receivers = {
            "operator": {},
            "admin": {}
        }
        self.message_templates = DISCORD_TEMPLATES

    async def on_ready(self):
        """Event for launching client
        Get admin and operator channels dinamically"""

        for channel in self.get_all_channels():
            if channel.type == discord.ChannelType.text:
                name = channel.name
                if name.find("operator") == 0:
                    self.receivers["operator"][name] = channel.id
                    print("Operator channel is got")
                elif name.find("admin") == 0:
                    self.receivers["admin"][name] = channel.id
                    print("Admin channel is got")
        print("Это получатели", self.receivers)

    async def form_message(self, message_code, message_data):
        message = self.message_templates[message_code]['text'].format(**message_data)
        return message

    async def send_mesage(self, reciever, message):
        channel_key = reciever
        channel = self.get_channel(self.receivers[reciever][channel_key])
        await channel.send(message)

    async def send_messages(self, message):
        """The function allows to send a message in channels\n
        Parameters:\n
        A message code : string\n
        Data : a dictionary of data for message template"""

        print("Работает discord отправитель")

        message_code, message_data = message
        message_code, message_data = message[message_code], message[message_data]

        message = await self.form_message(message_code, message_data)

        for receiver in self.message_templates[message_code]['receivers']:
            print(f'Message is sending to {receiver}')
            await self.send_mesage(receiver, message)
            print('Message is sent')

    async def start_working(self):
        pass
        # print("Начинаем цикл отправки сообщения")
        # await self.start(self.token)
