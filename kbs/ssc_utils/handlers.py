""" Этот модуль содержит обработчики запросов API сервера """

from aiohttp import web
import asyncio

from ..data.kiosk_modes.kiosk_modes import KioskModeNames
from ..data.server.server_const import ServerMessages, ServerConfig
from .handler_utils import HandlersUtils
from ..task_manager.pbm import pizza_bot_main


class Handlers(HandlersUtils):
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
    async def status_command_handler(cls, request):
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
        в response при запросе на api старт команды

        """

        print("Получен запрос на статус команды")
        params_list = await cls.get_params_from_request(request, ["command_uuid"])
        command_uuid,  = params_list
        try:
            future_result = await cls.process_future_result(command_uuid)
            return web.Response(text=future_result, content_type='text/plain')
        except KeyError:
            message = ServerMessages.UUID_COMMAND_NOT_FOUND
            raise web.HTTPBadRequest(text=message,
                                     content_type='text/plain')

    @classmethod
    async def can_receive_order(cls, request):
        """Этот метод определяет можно ли принимать заказы с точки зрения
        работоспособности оборудования и активации режима работы"""

        print("Получен запрос с оценкой можно ли работать")
        is_ok_eq = pizza_bot_main.equipment.is_able_to_cook
        current_state = pizza_bot_main.current_state
        if current_state == KioskModeNames.COOKINGMODE and is_ok_eq:
            response_text = "true"
        else:
            response_text = "false"
        return web.Response(text=response_text, content_type='text/plain')

    @classmethod
    async def new_order_handler(cls, request):
        """Этот метод обрабатывает запросы приема новых заказов в зависимости
        от текущего режима киоска, запускает создание нового заказа при необходимости.

        вид запроса {"check_code": "uuid4 заказа"}

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
          description: Тело запроса не найдено или ключ не распознан
        "406":
          description: "Заказ не может быть принят из-за текущего режима работы"
        "500":
          description: "Ошибка сервера"

        """
        params_list = await cls.get_params_from_request(request, ["check_code"])
        new_order_id, = params_list
        can_receive_new_order = await cls.is_open_for_new_orders(pizza_bot_main.current_state)
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
            except AttributeError as e:
                print("Вот такая ошибка возникла", e)
                message = ServerConfig.SERVER_ERROR_MESSAGE
                raise web.HTTPInternalServerError(text=message,
                                                  content_type='text/plain')
        else:
            message = ServerMessages.NOT_WORKING_HOURS
            raise web.HTTPNotAcceptable(text=message, content_type='text/plain')

    @classmethod
    async def turn_on_cooking_mode_handler(cls, request):
        """Этот метод обрабатывает запроса на включение режима готовки

        Description end-point

        produces:
        - json

        parameters: None

        responses:
        "200":
          description: uuid код для отслеживания статуса команды
        "400":
          description: режим включить нельзя, то есть активировано тестирование, ждем окончания
        "406":
          description: этот режим уже включен
         """
        print("Получили запрос на включение режима готовки")
        ALREADY_ON_STATES = (KioskModeNames.COOKINGMODE, KioskModeNames.BEFORECOOKING)
        current_kiosk_state = pizza_bot_main.current_state

        if current_kiosk_state in ALREADY_ON_STATES:
            await cls.response_state_is_already_on()

        elif current_kiosk_state == KioskModeNames.STANDBYMODE:
            response = await cls.turn_any_mode(pizza_bot_main.start_cooking_mode)
            return web.Response(text=response)

        elif current_kiosk_state == KioskModeNames.TESTINGMODE:
            await cls.response_state_is_busy(current_kiosk_state)

        else:
            print(current_kiosk_state)

    @classmethod
    async def start_full_testing_handler(cls, request):
        """Этот метод обрабатывает запрос на запуск полного тестирования системы

        Description end-point

        produces:
        - json

        responses:
        "200":
          description: uuid код для отслеживания статуса команды
        "400":
          description: режим включить нельзя, то есть активировано тестирование, ждем окончания
        "406":
          description: этот режим уже включен

        """
        print("Получили запрос на включение режима тестирования")
        current_kiosk_state = pizza_bot_main.current_state
        print("Вот этот стейт", current_kiosk_state)

        if current_kiosk_state == KioskModeNames.COOKINGMODE:
            await cls.response_state_is_busy(current_kiosk_state)

        elif current_kiosk_state == KioskModeNames.STANDBYMODE:
            params = [ServerConfig.FULL_TESTING_CODE]
            response = await cls.turn_any_mode(pizza_bot_main.start_testing, params)
            return web.Response(text=response, content_type='text/plain')

        elif current_kiosk_state == KioskModeNames.TESTINGMODE:
            await cls.response_state_is_already_on()

    @classmethod
    async def start_unit_testing_handler(cls, request):
        """Этот метод обрабатывает запрос на тестирование отдельного узла
        не доделано

        Description end-point

        produces:
        - text/plain

        parameters:
        - in: body
          name: body
          description: Тестирование отдельного узла
          required: true
          schema:
            type: object
            properties:
              testing_type:
                type: string value: "UNIT"
              unit_type:
                type: string
              unit_id:
                type: string (uuid4)

        responses:
        "200":
          description: uuid код для отслеживания статуса команды
        "204":
          description: Тело запроса не найдено или ключ не совпадает
                       разделить потом на 2 ошибки
        "400":
          description: Киоск занят, включить не можем

        """

        current_kiosk_state = pizza_bot_main.current_state
        if current_kiosk_state == KioskModeNames.STANDBYMODE:
            key_list = ["testing_type", "unit_type", "unit_id"]
            params_list = await cls.get_params_from_request(request, key_list)
            response = await cls.turn_any_mode(pizza_bot_main.start_testing, params_list)
            return web.Response(text=response, content_type='application/json')
        else:
            await cls.response_state_is_busy(current_kiosk_state)

    @classmethod
    async def unit_activation_handler(cls, request):
        """Этот метод обрабатывает активацию отдельного узла

        Description end-point

        produces:
        - text/plain

        parameters:
        - in: body
          name: body
          description: Активирование отдельного узла
          required: true
          schema:
            type: object
            properties:
              unit_type:
                type: string
              unit_id:
                type: string (uuid4)

        responses:
        "200":
          description: успешно обновлено
        "204":
          description: Тело запроса не найдено или ключ не совпадает
                       разделить потом на 2 ошибки

        """
        key_list = ["unit_type", "unit_id"]
        params_list = await cls.get_params_from_request(request, key_list)
        message = await pizza_bot_main.unit_activation(params_list)
        return web.Response(text=message, content_type='text/plain')
