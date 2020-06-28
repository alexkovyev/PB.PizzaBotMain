"""Тут должно быть описание logger из aiologger с записью в файл"""

# не заработало, ошибка

import asyncio
import logging
from aiologger import Logger
from aiologger.handlers.files import AsyncFileHandler
from tempfile import NamedTemporaryFile


logger = Logger.with_default_handlers(name='pizza_bot-logger')
logger.level = logging.DEBUG
temp_file = NamedTemporaryFile()
handler = AsyncFileHandler(filename=temp_file.name)

