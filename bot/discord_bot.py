import discord
import asyncio
import os
import time
from dotenv import load_dotenv
from discord import ChannelType
 
class BotAccess(discord.Client):
    """This class represents Discord Client that allows to send notifications
    when critical or emergency situations happenning"""

    def __init__(self):
        """Config file *.env is required"""
        super().__init__(help_attrs=dict(hidden=True))
        file_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(file_path):
            load_dotenv(file_path)
            self.token = os.getenv('TOKEN')
            self.prefix = '!'
            self.channelsAdmin = {}
            self.channelsOperator = {}
            print('Client created')
        else:
            print('Config file was not found')
            
    async def on_ready(self):
        """Event for launching client\n
        Get admin and operator channels dinamically"""
        print('Logged in as {0}!'.format(self.user.name))
        for channel in self.get_all_channels():
            if channel.type == ChannelType.text:
                name = channel.name
                if name.find('operator') == 0:
                    self.channelsOperator[name] = channel.id
                    print('Operator channel is got')
                elif name.find('admin') == 0:
                    self.channelsAdmin[name] = channel.id
                    print('Admin channel is got')
        await self.send('message', 'dev', True)

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        print('Message from {0.author} : {0.content}'.format(message))
        await message.channel.send('Hello {0.author.mention}'.format(message))

    async def send(self, message, pointKey, is_all_channel_msg = False):
        """The function allows to send a message in channels\n
        Parameters:\n
        A message : string\n
        A determiner of channels, depends on a kiosk number ('dev' now): string\n
        Is a message should be sent in operator's channel or not: bool
            False by default"""
        channelKey = 'admin_' + pointKey
        if not pointKey or not message or not (channelKey in self.channelsAdmin):
            return
        canal = self.get_channel(self.channelsAdmin[channelKey])
        print('Channel name is', canal.name)
        await canal.send(message)
        print('Message is sent')
        if is_all_channel_msg:
            channelKey = 'operator_' + pointKey
            if not (channelKey in self.channelsOperator):
                return
            canal = self.get_channel(self.channelsOperator[channelKey])
            print('Channel name is', canal.name)
            message = f"""```Excel\n{message}```"""
            await canal.send(message)
            print("Message is sent")

async def first(_channel):
    print('timer starts')
    await asyncio.sleep(60)
    print('timer is over')
    await client.send("111")    

async def second(_token):
    print('try start')
    await client.start(_token)

async def main(t, c):
    print('preraring')
    task1 = asyncio.create_task(first(c)),
    task2 = asyncio.create_task(second(t))
    print('started')
    await asyncio.gather(task1, task2)

#client = BotAccess()
#loop = asyncio.get_event_loop()
#loop.run_until_complete(main(client.token, client.channel))
#asyncio.run(main(TOKEN, CHANNEL))
client = BotAccess()
client.run(client.token)
#client.run('NzA2MTAwNjAwODUyNDQ3Mjk1.Xq1Vxg.4Vg1O4thnlsdRb0fWqCq8K9IfIg')
