"""Пока тут собрана информация о рецепте.
Доделано по "сути", не сделан рефакторинг и проверка на адекватность
"""
import asyncio
import time

from kbs.ra_api.RA import RA
from kbs.ra_api.RA import RAError
from kbs.cntrls_api.ControllerBus import Controllers


class ConfigMixin(object):
    """Временное хранение идентификаторов оборудования"""
    SLICING = "станция нарезки"
    CAPTURE_STATION = "место захватов"
    PRODUCT_CAPTURE_ID = "захват для продуктов"
    PACKING = "станция упаковки"
    GIVE_OUT = "пункт выдачи"
    GARBAGE_STATION = "пункт утилизации"
    STOP_STATUS = "failed_to_be_cooked"


class ToolsMixin(object):

    @staticmethod
    async def is_need_to_change_gripper(current_gripper: str, required_gripper: str):
        """метод проверяет нужно ли менять захват ra_api
        """
        return True if str(current_gripper) != required_gripper else False

    async def chain_execute(self, chain_list, equipment):
        """Метод, вызывающий выполнение чейнов из списка
        Чейн - это какая то непрерывная последовательность действий.
        """
        try:
            for chain in chain_list:
                if not self.is_dish_failed:
                    chain, params = chain
                    await chain(params, equipment)
                else:
                    break
        except RAError:
            print("Ошибка века")
            await self.mark_dish_as_failed()

    @staticmethod
    async def is_need_to_dance(limit, time_limit):
        """

        :param limit:
        :param time_limit:
        :return:
        """
        if limit is not None and time_limit is not None:
            time_to_dance = time_limit - time.time()
            return time_to_dance if time_to_dance >1 else False
        else:
            return False

    async def prepare_cooking(self):

        lock = asyncio.Lock()
        async with lock:
            await self.mark_dish_as_started()


class BaseRA(ToolsMixin):
    """ Это класс дописать """

    @staticmethod
    async def get_current_position():
        """Этот метод возвращает место, куда едет RA"""

        return await RA.get_current_position()

    @staticmethod
    async def get_movement_duration(place_from, place_to, time_limit=None):
        """ Метод получает варианты длительности передвижения, выбирает тот, который
        удовлетворяет условиям
        :param place_from: str
        :param place_to: str
        :param time_limit: datetime.time
        :return: int
        :raise RAError

        """
        possible_duration = await RA.get_position_move_time(place_from, place_to)
        if possible_duration and time_limit:
            time_gap = time_limit - time.time()
            time_options = list(filter(lambda t: t <= time_gap, possible_duration))
            return max(time_options) if time_options else min(possible_duration)
        elif possible_duration:
            return min(possible_duration)
        if not possible_duration:
            raise RAError

    @staticmethod
    async def get_atomic_chain_duration(atomic_info):
        """ Этот метод получает длительность группы атомарных действий в сек
        :param atomic_info:
        :return:

        Где используем этот метод????? Удалить?
        """
        duration = await RA.get_atomic_action_time(**atomic_info)

        if not duration:
            raise RAError
        return duration

    @classmethod
    async def atomic_chain_execute(cls, atomic_params_dict, *args):
        """Этот метод выполняет группу атомарных действий
        :param atomic_params_dict: dict с параметрами (name, place)

        """
        duration = await cls.get_atomic_chain_duration(atomic_params_dict)
        try:
            await RA.start_atomic_action(**atomic_params_dict)
            print("Успешно выполнили атомарное действие", atomic_params_dict["name"])
        except RAError:
            print("Ошибка атомарного действия")


class BaseActionsRA(BaseRA, ConfigMixin):

    async def move_to_object(self, move_params, equipment):
        """Эта функция описывает движение до определенного места.

        ПЕРЕПИСАТЬ документацию

        :param: tuple (place: uuid, limit: bool)
        limit - это флаг для выбора времени на перемещения.
        ra_api одно и тоже движение может выполнить за разное время: мин возможное и "с танцами"
        сам временной лимит, то есть время, в которое нужно приехать
        в конечную точку содержится в self.time_limit

        Если лимит True, то движение туда запускается по мин времени, а обратно
        в зависимости от оставшегося времени. Если есть свободное, "танцуем с продуктом"

        """
        print("Начинаем чейн движения")
        place_to, limit = move_params
        current_location = await self.get_current_position()
        is_limit_active = True if limit and equipment.cut_station.be_free_at else False
        time_limit = equipment.cut_station.be_free_at if is_limit_active else None
        # получаем все возможные временные варианты доезда до
        try:
            duration = await self.get_movement_duration(current_location,
                                                        place_to,
                                                        time_limit)
            await RA.position_move(place_to, duration)
            dance_time = await self.is_need_to_dance(limit, equipment.cut_station.be_free_at)
            if dance_time:
                print("начинаем танцевать дополнительно", dance_time, time.time())
                await RA.dance_for_time(dance_time)
        except RAError:
            print("Не найден маршрут. Что делать???")

    async def bring_half_staff(self, cell_location_tuple, equipment, *args):
        """

        :param cell_location_tuple: ('d4', (3, 4))
        :param args:
        :return:
        """
        print("Начинаем везти продукт")
        cell_location, half_staff_position = cell_location_tuple
        atomic_params = {"name": "get_product",
                         "place": "fridge",
                         "obj": "onion",
                         "cell": cell_location,
                         "position": half_staff_position,
                         }

        move_params_to_fridge = (cell_location, False)
        move_params_to_cut = (self.SLICING, True)

        what_to_do = [
            (self.move_to_object, move_params_to_fridge),
            (self.atomic_chain_execute, atomic_params),
            (self.move_to_object, move_params_to_cut),
        ]
        await self.chain_execute(what_to_do, equipment)
        print("*!*!*!*! Закончили с ингредиентом начинки", self.status, time.time())

    async def change_gripper(self, required_gripper,  equipment):
        """метод, запускающий смену захвата при необходимости """

        current_gripper = await RA.get_current_gripper()
        is_needed_to_change_gripper = await self.is_need_to_change_gripper(current_gripper, required_gripper)
        print("Проверяем, нужно ли менять захват", is_needed_to_change_gripper)
        if is_needed_to_change_gripper:
            await self.move_to_object((self.CAPTURE_STATION, None), equipment)
            while current_gripper != required_gripper:
                # эмуляция работы)
                if current_gripper is not None:
                    await self.atomic_chain_execute({"place": "gripper_unit", "name": "set_gripper"})
                    await self.atomic_chain_execute({"place": "gripper_unit", "name": "get_gripper"})
                    # Потом удалить, эмуляция работы
                    current_gripper = required_gripper
                else:
                    await self.atomic_chain_execute({"place": "gripper_unit", "name": "get_gripper"})
                    # Потом удалить, эмуляция работы
                    current_gripper = required_gripper

    async def get_vane_from_oven(self, *args):
        """Этот метод запускает группу атомарных действий ra_api по захвату лопатки из печи"""
        oven = self.oven_unit
        atomic_params = {"name": "get_vane_from_oven",
                         "place": oven}
        await self.atomic_chain_execute(atomic_params)

    async def set_vane_in_oven(self, *args):
        """Этот метод запускает группу атомарных действий ra_api по размещению лопатки в печи"""
        oven_id = self.oven_unit
        atomic_params = {"name": "set_shovel",
                         "place": oven_id}
        for arg in args:
            if arg == "heating":
                asyncio.create_task(self.controllers_turn_heating_on())
        await self.atomic_chain_execute(atomic_params)

    async def leave_vane_in_cut_station(self, *args):
        """отдаем команду оставить лопатку в станции нарезки"""
        atomic_params = {"name": "set_shovel",
                         "place": self.SLICING}
        await self.atomic_chain_execute(atomic_params)

    # не объединено с выше в 1, так как обработка ошибок может быть разная
    async def take_vane_from_cut_station(self, *args):
        """отдаем команду взять лопатку в станции нарезки"""
        atomic_params = {"name": "get_shovel",
                         "place": self.SLICING}
        await self.atomic_chain_execute(atomic_params)

    async def control_dough_position(self, *args):
        """отдаем команду на поправление теста"""
        atomic_params = {"name": "get_dough",
                         "place": self.dough.halfstuff_cell}
        await self.atomic_chain_execute(atomic_params)

    async def put_half_staff_in_cut_station(self, *args):
        """Этот метод опускает п-ф в станцию нарезки"""
        print("Начинаем размещать продукт в станции нарезки", time.time())
        print(args)
        _, equipment = args
        print("Станция нарезки свободна", equipment.cut_station.is_free.is_set())
        atomic_params = {
            "name": "set_product",
            "place": self.SLICING
        }
        while not equipment.cut_station.is_free.is_set() and not self.is_dish_failed:
            print("Танцуем с продуктом")
            await asyncio.sleep(1)
            # добавить вызов ra_api танец с продуктом
        await self.atomic_chain_execute(atomic_params)

    async def dish_packaging(self):
        """Этот метод запускает группу атомарных действий по упаковке пиццы"""
        print("Начинаем упаковывать блюдо ra_api", time.time())
        atomic_params = {
            "name": "pack_pizza",
            "place": self.PACKING
        }
        await self.atomic_chain_execute(atomic_params)

    async def dish_extradition(self):
        """Этот метод запускает группу атомарных действий по выдаче пиццы"""
        print("Выдаем пиццу в узел выдачи", time.time())
        atomic_params = {
            "name": "set_pizza",
            "place": self.GIVE_OUT
        }
        await self.atomic_chain_execute(atomic_params)

    async def switch_vane(self):
        """Этот метод запускает группу атомарных действий по смене лопакок при выдаче"""
        print("Запускаем смену лопаток с выдачи на для пиццы")
        atomic_params = {
            "name": "get_shovel",
            "place": self.PACKING
        }
        await self.atomic_chain_execute(atomic_params)


class BaseActionsControllers():

    async def get_dough(self, *args):
        """отдает команду контролеру получить тесто"""
        print("получаем тесто у контрллеров")
        dough_point = self.dough.halfstuff_cell
        chain_result = await Controllers.give_dough(dough_point)
        if chain_result:
            print("взяли тесто у контроллеров")
        else:
            print("Ошибка получения теста у контроллеров")
            await self.mark_dish_as_failed()
        # запускает метод списать п\ф
        print("СТАТУС блюда после получения теста", self.status)

    async def give_sauce(self, equipment):
        """Вызов метода контроллеров для поливания соусом"""
        print("Начинаем поливать соусом", time.time())
        equipment.cut_station.is_free.clear()
        recipe = self.sauce.sauce_cell
        result = await Controllers.give_sauce(recipe)
        if result:
            print("успешно полили соусом")
            equipment.cut_station.is_free.set()
        else:
            await self.mark_dish_as_failed()
        print("СТАТУС блюда после поливки соусом", self.status)

    async def cut_half_staff(self, cutting_program, equipment):
        print("Начинаем этап ПОРЕЖЬ продукт", time.time())
        duration = cutting_program["duration"]
        program_id = cutting_program["program_id"]
        print("Время начала нарезки п\ф", time.time())
        equipment.cut_station.be_free_at = time.time() + cutting_program["duration"]
        equipment.cut_station.is_free.clear()
        result = await Controllers.cut_the_product(program_id)
        if result:
            print("успешно нарезали п\ф", time.time())
            equipment.cut_station.is_free.set()
            equipment.cut_station.be_free_at = None
            print("СНЯТ временой ЛИМИТ в", time.time())
        else:
            print("---!!! Не успешно нарезали п\ф")
            await self.mark_dish_as_failed()
        print("СТАТУС блюда в нарезке", self.status)

    async def give_paper(self):
        print("Контроллеры начинают выдавать бумагу", time.time())
        result = await Controllers.give_paper()
        if result:
            pass
        else:
            print("Неудача с бумагой")
            await self.mark_dish_as_failed()

            # расписать какая ошибка: - замятие бумаги или полная поломка
            # если замятие, добавить вызов ra_api на уборку бумаги

    async def controllers_oven(self, oven_mode, recipe):
        """Это метод контроллеров, оперирующий печами
        При вызове метода, контроллеры возвращают результат футуры,
        содержащий изменения времени готовности блюд. Это вызвано тем,
        что разные режимы потребляют разную мощность и максимальной мощности
        может не хватить на одновременное приготовление нескольких блюд.
        Обработка футур пока не реализована
        """
        time_changes = asyncio.get_running_loop().create_future()
        operation_result = asyncio.get_running_loop().create_future()
        asyncio.create_task(Controllers.start_baking(self.oven_unit.oven_id, oven_mode, recipe, time_changes,
                                                     operation_result))
        while not time_changes.done():
            await asyncio.sleep(0.0001)
        print("Футура доделала", time.time())
        await self.time_changes_handler(time_changes)
        return operation_result

    async def controllers_turn_heating_on(self):
        """Метод запускает прогрев печи"""
        print("Начинаем прогрев печи", time.time())

        oven_mode = "pre_heating"
        recipe = self.pre_heating_program
        operation_result = await self.controllers_oven(oven_mode, recipe)
        return operation_result

    async def controllers_bake(self, *args):
        """Метод запускает выпечку"""
        print("Начинаем выпечку", time.time())
        oven_mode = "baking"
        recipe = self.baking_program
        self.status = "baking"
        operation_result = await self.controllers_oven(oven_mode, recipe)
        print("Это результат выпечки", operation_result)
        while not operation_result.done():
            await asyncio.sleep(0)
        self.is_dish_ready.set()
        print("БЛЮДО ГОТОВО")
        self.status = "ready"
        self.oven_unit.status = "waiting_15"
        print("Это результат установки", self.is_dish_ready.is_set())

    async def turn_oven_heating_on(self, turn_on_event):
        while turn_on_event.is_set():
            pass


class DishRecipe(BaseActionsRA, BaseActionsControllers):

    async def prepare_dough_and_sauce(self, *args):
        """Метод рецепта, описываюший этап возьи тесто и полей соусом
        Это bound-method к блюду, поэтому доступны все атрибуты
        экземпляра класса Dish
        """
        print(f"PBM {time.time()} - Начинается chain Возьми ТЕСТО")
        print()

        _, equipment = args

        to_do = ((self.change_gripper, "None"),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.get_vane_from_oven, None),
                      (self.move_to_object, (self.SLICING, None)),
                      (self.get_dough, None),
                      (self.control_dough_position, None),
                      (self.move_to_object, (self.SLICING, None)),
                      (self.leave_vane_in_cut_station, None),
        )

        await self.prepare_cooking()
        await self.chain_execute(to_do, equipment)

        print(f"PBM {time.time()} - Закончили с ТЕСТОМ, статус блюда {self.status}")
        print()

        if not self.is_dish_failed:
            asyncio.create_task(self.give_sauce(equipment))
            print(f"PBM {time.time()} - Запустили политие соусом в очередь")
            print()

    async def prepare_filling_item(self, *args):
        """Чейн по доставке и нарезки 1 п\ф
        args: (params, equipment)

        """
        # print("Это аргс из начинки", args)
        filling_data, equipment = args
        filling_item = filling_data["id"]
        cutting_program = filling_data["cut_program"]
        storage_adress = filling_data["location"]
        is_last_item = filling_data["is_last"]

        to_do = (
            (self.change_gripper, "product"),
            (self.bring_half_staff, storage_adress),
            (self.put_half_staff_in_cut_station, None),
                 )

        print(f"PBM - {time.time()} Начинаем готовить {filling_item.upper()}")

        if is_last_item:
            # посчитать время на текущую операцию
            # посчитать время на нарезку
            # посчитать время на доставку лопатки в печь
            # определить время включения прогрева
            pass

        await self.chain_execute(to_do, equipment)

        if not self.is_dish_failed:
            asyncio.create_task(self.cut_half_staff(cutting_program, equipment))
            print(f"PBM {time.time()} - Запустили нарезку п-ф в очередь")
            print()

    async def time_calculation(self, chain_to_do):
        for item in chain_to_do:
            pass
        pass

    async def start_baking(self, *args):
        """Этот метод транспортрует лопатку в печь и запускает выпечку"""
        print("Начинаем чейн Вези лопатку в печь")
        print("Это аргс из начинки", args)
        _, equipment = args

        chain_list = [(self.change_gripper, "None"),
                      (self.move_to_object, (self.SLICING, None)),
                      (self.take_vane_from_cut_station, None),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.set_vane_in_oven, "heating"),
                      ]

        print("СТАНЦИЯ НАРЕЗКИ СВОБОДНА", equipment.cut_station.is_free.is_set())
        while not equipment.cut_station.is_free.is_set():
            # try:
            #     first_task_to_do = args[1].high_priority_queue.get_nowait()
            # except asyncio.QueueEmpty:
            #     print("Доставлять нечего, поработаем в другом месте")
            # try:
            #     task_to_do = args[1].low_priority_queue.get_nowait()
            # except asyncio.QueueEmpty:
            #     print("Мыть ничего не нужно, тоска")
            print("Танцеуем")
            await RA.dance()

        # asyncio.create_task(self.controllers_turn_heating_on())
        await self.chain_execute(chain_list, equipment)
        print("Оставили лопатку в печи", time.time())
        self.status = "baking"
        if self.status != "failed_to_be_cooked":
            asyncio.create_task(self.controllers_bake())
        print("ЗАКОНЧИЛИ С БЛЮДОМ", time.time())
        print("СТАТУС блюда после доставки лопатки в печь", self.status)

    async def make_crust(self):
        print("Начинаем разогрев пиццы")
        oven_mode = "make_crust"
        recipe = self.make_crust_program
        time_changes = asyncio.get_running_loop().create_future()
        await self.time_changes_handler(time_changes)
        operation_results = await Controllers.start_baking(self.oven_unit.oven_id, oven_mode, recipe, time_changes)
        return operation_results

    async def dish_packing_and_deliver(self):
        print("Начинаем упаковку пиццы")
        chain_list = [(self.change_gripper, "None"),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.get_vane_from_oven, None),
                      (self.move_to_object, (self.PACKING, None)),
                      (self.dish_packaging, None),
                      (self.move_to_object, (self.pickup_point_unit, None)),
                      (self.dish_extradition, None),
                      (self.move_to_object, (self.PACKING, None)),
                      (self.switch_vane, None),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.set_vane_in_oven, None),
                      ]
        await self.chain_execute(chain_list)
        print("Закончили упаковку и выдачу пиццы")

    async def throwing_dish_away(self):
        print("Запускаем выбрасывание блюда", time.time())
        chain_list = [(self.change_gripper, "None"),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.get_vane_from_oven, None),
                      (self.move_to_object, (self.GARBAGE_STATION, None)),
                      (self.move_to_object, (self.oven_unit, None)),
                      ]
        await self.chain_execute(chain_list)
        self.oven_unit.status = "free"
        self.oven_unit.dish = None
        self.status = self.STOP_STATUS
        print("Закончили выбрасывание блюда")

    async def switch_vanes(self, broken_oven_unit):
        print("Запускаем смену лопаток между печами")
        # не доделано
        chain_list = [(self.move_to_object, (broken_oven_unit, None)),

                      (),
                      ]

    async def switch_vane_cut_oven(self, new_oven_id, old_oven_id, *args):
        print("Меняем лопатку между станцией нарезки и печью")
        chain_list = [(self.move_to_object, (new_oven_id, None)),
                      (self.get_vane_from_oven, new_oven_id),
                      (self.move_to_object, (old_oven_id, None)),
                      (self.set_vane_in_oven, old_oven_id)
                      ]
        await self.chain_execute(chain_list)
        # что будет если неудачно?