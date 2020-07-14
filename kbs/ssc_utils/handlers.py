""" Этот модуль содержит обработчики запросов апи сервера """

from aiohttp import web
import asyncio

from ..data.kiosk_modes.kiosk_modes import KioskModeNames
from ..data.server.server_const import ServerMessages, ServerConfig
from .handler_utils import HandlersUtils
from ..task_manager.pbm import pizza_bot_main


class Handlers(object):
    """Это основной класс Handlers"""

    @classmethod
    async def kiosk_current_state_handler(cls, request):
        """Этот метод обрабатывает запрос на Апи о получении данных о текущем статусе киоска.

        Description end-point

        produces:
        - text/plain

        parameters:
        - None

        responses:
        "200":
          description: Название текущего режима работы киоска

        """
        print("Получили запрос текущего статуса киоска")
        print(pizza_bot_main.current_state)
        return web.Response(text=pizza_bot_main.current_state, content_type='text/plain')

    @classmethod
    async def new_order_handler(cls, request):
        """Этот метод обрабатывает запросы приема новых заказов в зависимости от текущего режима киоска,
        запускает создание нового заказа при необходимости.

        Description end-point

        produces:
        - text/plain

        parameters:
        - in: body
          name: body
          description: Новый заказ пользователя
          required: true
          schema:
            type: object
            properties:
              check_code:
                type: string

        responses:
        "200":
          description: "Заказ уже находится в обработке"
        "201":
          description: "Заказ успешно принят"
        "204":
          description: Тело запроса не найдено
        "406":
          description: "Заказ не может быть принят из-за текущего режима работы"
        "500":
          description: "Ошибка сервера"

        """
        params_list = await HandlersUtils.get_params_from_request(request, ["check_code"])
        new_order_id, = params_list
        can_receive_new_order = await pizza_bot_main.is_open_for_new_orders()
        if can_receive_new_order:
            try:
                is_it_new_order = await pizza_bot_main.current_instance.checking_order_for_double(new_order_id)
                if is_it_new_order:
                    await asyncio.create_task(pizza_bot_main.current_instance.create_new_order(new_order_id))
                    message = ServerMessages.ORDER_CREATED_MESSAGE
                    raise web.HTTPCreated(text=message, content_type='text/plain')
                else:
                    message = ServerMessages.DOUBLE_ORDER_MESSAGE
                    raise web.HTTPOk(text=message, content_type='text/plain')
            except AttributeError:
                print("Не создан инстанс cooking mode или метод не найден")
                message = ServerConfig.SERVER_ERROR_MESSAGE
                raise web.HTTPInternalServerError(text=message,
                                                  content_type='text/plain')
        else:
            message = ServerMessages.NOT_WORKING_HOURS
            raise web.HTTPNotAcceptable(text=message, content_type='text/plain')

    @staticmethod
    async def status_command_handler(request):
        """Этот метод обрабатывает запрос о том, выполнена ли команда, отправленная на АПИ

        Description end-point

        produces:
        - text/plain

        parameters:
        - in: body
          name: body
          description: Запрос о статусе завершения отправленной команды
          required: true
          schema:
            type: object
            properties:
              command_uuid:
                type: string

        responses:
        "200":
          description: статус исполнения команды
        "204":
          description: тело запроса не найдено
        "400":
          description: uuid не найден
        "500":
          description: "Ошибка сервера"

        command_uuid - это уникальный идентификатор команды, который генерируется сервером
        в responce при запросе на api старт команды

        """

        print("Получен запрос на статус команды")
        params_list = await HandlersUtils.get_params_from_request(request, ["command_uuid"])
        command_uuid,  = params_list
        try:
            future_result = await HandlersUtils.process_future_result(command_uuid)
            return web.Response(text=future_result, content_type='text/plain')
        except KeyError:
            message = ServerMessages.UUID_COMMAND_NOT_FOUND
            raise web.HTTPBadRequest(text=message,
                                     content_type='text/plain')

    @staticmethod
    async def turn_on_cooking_mode_handler(request):
        """Этот метод обрабатывает запроса на включение режима готовки

        Description end-point

        produces:
        - json

        parameters: None

        responses:
        "200":
          description: статус исполнения команды
        "400":
          description: режим включить нельзя, то есть активировано тестирование, ждем окончания
        "406":
          description: этот режим уже включен
         """
        print("Получили запрос на включение режима готовки")
        ALREADY_ON_STATES = (KioskModeNames.COOKINGMODE, KioskModeNames.BEFORECOOKING)
        current_kiosk_state = pizza_bot_main.current_state

        if current_kiosk_state in ALREADY_ON_STATES:
            await HandlersUtils.response_state_is_already_on()

        elif current_kiosk_state == KioskModeNames.STANDBYMODE:
            response = await HandlersUtils.turn_any_mode(pizza_bot_main.cooking_mode_start)
            return web.Response(text=response)

        elif current_kiosk_state == KioskModeNames.TESTINGMODE:
            await HandlersUtils.response_state_is_busy(current_kiosk_state)

    @staticmethod
    async def start_full_testing_handler(request):
        """Этот метод обрабатывает запрос на запуск полного тестирования системы

        Description end-point

        produces:
        - json

        parameters: None

        responses:
        "200":
          description: статус исполнения команды
        "400":
          description: режим включить нельзя, то есть активировано тестирование, ждем окончания
        "406":
          description: этот режим уже включен

        """
        print("Получили запрос на включение режима тестирования")
        current_kiosk_state = pizza_bot_main.current_state

        if current_kiosk_state == KioskModeNames.COOKINGMODE:
            await HandlersUtils.response_state_is_busy(current_kiosk_state)

        elif current_kiosk_state == KioskModeNames.STANDBYMODE:
            params = {"testing_type": ServerConfig.FULL_TESTING_CODE}
            response = await HandlersUtils.turn_any_mode(pizza_bot_main.testing_start, params)
            return web.Response(text=response, content_type='text/plain')

        elif current_kiosk_state == KioskModeNames.TESTINGMODE:
            await HandlersUtils.response_state_is_already_on()

    @staticmethod
    async def start_unit_testing_handler(request):
        """Этот метод обрабатывает запрос на тестирование отдельного узла"""
        current_kiosk_state = pizza_bot_main.current_state
        if current_kiosk_state == KioskModeNames.STANDBYMODE:
            key_list = ["testing_type", "unit_type", "unit_id"]
            params_list = await HandlersUtils.get_params_from_request(request, key_list)
            # await HandlersUtils.if_no_body_error_response(request)
            # request_body = await request.json()
            # params = {"testing_type": ServerConfig.UNIT_TESTING_CODE,
            #           "unit_type": request_body["unit_type"],
            #           "unit_id": request_body["unit_id"]}
            response = await HandlersUtils.turn_any_mode(pizza_bot_main.testing_start, params_list)
            return web.Response(text=response, content_type='application/json')
        else:
            await HandlersUtils.response_state_is_busy(current_kiosk_state)

    @staticmethod
    async def unit_activation_handler(request):
        """Этот метод обрабатывает активацию отдельного узла"""
        key_list = ["unit_type", "unit_id"]
        params_list = await HandlersUtils.get_params_from_request(request, key_list)
        # if not request.body_exists:
        #     raise web.HTTPNoContent
        # request_body = await request.json()
        # params = {"unit_type": request_body["unit_type"],
        #           "unit_id": request_body["unit_id"]}
        message = await pizza_bot_main.unit_activation(params_list)
        return web.Response(text=message, content_type='text/plain')
