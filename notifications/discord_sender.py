"""Этот модуль отправляет сообщения в Discord
В Discord есть 2 текстовых канала для оператора и администратора."""

import discord

from data.discord_confg.discord_confg import DiscordConfg


operator_channel_name = DiscordConfg.DISCORD_OPERATOR_CHANNEL_NAME
admin_channel_name = DiscordConfg.DISCORD_ADMIN_CHANNEL_NAME


class DiscordBotAccess(discord.Client):
    """Это основной класс клиента Discord"""

    def __init__(self):
        super().__init__()
        self.token = DiscordConfg.DISCORD_TOKEN
        self.receivers = {
            operator_channel_name: {},
            admin_channel_name: {}
        }
        self.message_templates = DiscordConfg.DISCORD_TEMPLATES

    async def on_ready(self):
        """Этот метод подгружает данные каналов для отправки динамчески"""

        for channel in self.get_all_channels():
            if channel.type == discord.ChannelType.text:
                name = channel.name
                if name.find(operator_channel_name) == 0:
                    self.receivers[operator_channel_name][name] = channel.id
                    print("Канал оператора подключен")
                elif name.find(admin_channel_name) == 0:
                    self.receivers[admin_channel_name][name] = channel.id
                    print("Канал админа подключен")

    async def form_message(self, message_code, message_data):
        """Этот метод подставляет данные в шаблон и формирует текстовое сообщение
        :param message_code: str
        :param message_data: dict
        """
        message = self.message_templates[message_code]['text'].format(**message_data)
        return message

    async def send_mesage(self, reciever, message):
        """Этот метод отправляет сообщение в нужный канал
        :param reciever: str
        :param message: str
        """
        channel_key = reciever
        channel = self.get_channel(self.receivers[reciever][channel_key])
        await channel.send(message)

    async def send_messages(self, message):
        """Этот метод разбирает, в какие каналы нужно отправить сообщение,
         запускает его формирование и отправку
        :param message: dict вида
                message = {
                           "message_code": "out_of_stock",
                           "message_data": {'id': '1',
                                            'address': 'here',
                                            'halfstaff_name': 'пельмени',
                                             'N': '1',
                                             'min_qt': '3'}
                           }
        """

        message_code, message_data = message
        message_code, message_data = message[message_code], message[message_data]

        message = await self.form_message(message_code, message_data)

        for receiver in self.message_templates[message_code]['receivers']:
            print(f'Message is sending to {receiver}')
            await self.send_mesage(receiver, message)
            print('Message is sent')

    async def start_working(self):
        """Это основная функция запуска бота"""
        await self.start(self.token)
