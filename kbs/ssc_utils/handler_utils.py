"""
Это модуль вспомогательных инструментов
"""

from aiohttp import web
import asyncio
import uuid

from ..data.server.server_const import ServerMessages
from ..task_manager.pbm import pizza_bot_main


class HandlersUtils(object):
    """ Это вспомогательные методы по подготовке ответа на запросы
    """

    @staticmethod
    async def if_no_body_error_response(request):
        """

        :param request:
        """
        if not request.body_exists:
            raise web.HTTPNoContent(text="Пустое тело запроса")

    @classmethod
    async def get_params_from_request(cls, request, params_keys_value):
        """

        :param request:
        :param param_keys_list:
        :return:
        """
        await cls.if_no_body_error_response(request)
        request_body = await request.json()
        return request_body

    @staticmethod
    async def get_future_result(future):
        """Этот метод проверяет, выполнена ли команда и формирует результат"""
        if future.done():
            try:
                future_result = future.result()
            except asyncio.CancelledError:
                future_result = ServerMessages.CANCELLED_FUTURE_MESSAGE
        else:
            future_result = ServerMessages.PENDING_FUTURE_RESULT
        return future_result

    @staticmethod
    async def is_future_succeed(future_result):
        """ Метод проверяет успешно ли выполнена футура
        :param future_result:
        :return: bool
        """
        return True if future_result == ServerMessages.SUCCEED_FUTURE_RESULT_CODE else False

    @classmethod
    async def proceed_future_result(cls, command_uuid):
        """ Этот метод ....

        :param command_uuid: str
        """
        future = pizza_bot_main.command_status[command_uuid]
        future_result = await cls.get_future_result(future)
        is_future_succeed = await cls.is_future_succeed(future_result)
        if is_future_succeed:
            pizza_bot_main.command_status.pop(command_uuid)
        return future_result

    @staticmethod
    async def response_state_is_already_on():
        """Это шаблон ответа, что запрашиваемый режим уже включен"""
        print("Этот режим уже включен")
        message = ServerMessages.STATE_IS_ON_ALREADY
        raise web.HTTPNotAcceptable(text=message)

    @staticmethod
    async def response_state_is_busy(kiosk_state):
        """Это шаблон ответа, что запрашиваемый режим включить нельзя
        """
        message = f"Активирован режим {kiosk_state}, включить не можем"
        raise web.HTTPBadRequest(text=message)

    @staticmethod
    async def create_result_future():
        """Этот метод создает футуру на каждый запрос выполнения команды, отпарвленный на API
        добавляет в словарь всех футур """
        operation_result = asyncio.get_running_loop().create_future()
        operation_result_uuid = str(uuid.uuid4())
        pizza_bot_main.command_status[operation_result_uuid] = operation_result
        return operation_result_uuid, operation_result

    @classmethod
    async def turn_any_mode(cls, task_name, *args):
        """Этот метод включает заданный режим киоска по запросу, отправленному на API
        :param task_name: небходимый метод
        """
        print("Ок, включаем")
        operation_result_uuid, operation_result = await cls.create_result_future()
        asyncio.create_task(task_name(operation_result, *args))
        response = f"uuid:{operation_result_uuid}"
        return response
