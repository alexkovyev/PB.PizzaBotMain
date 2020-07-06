"""Пока тут собрана информация о рецепте.
Доделано по "сути", не сделан рефакторинг и проверка на адекватность
"""
import asyncio
import time

from RA.RA import RA
from RA.RA import RAError
from controllers.ControllerBus import Controllers

from config.config import OVEN_LIQUIDATION_TIME, OVEN_FREE_WAITING_TIME


class ConfigMixin(object):
    """Временное хранение идентификаторов оборудования"""
    SLICING = "станция нарезки"
    CAPTURE_STATION = "место захватов"
    PRODUCT_CAPTURE_ID = "захват для продуктов"
    PACKING = "станция упаковки"
    GIVE_OUT = "пункт выдачи"
    GARBAGE_STATION = "пункт утилизации"
    STOP_STATUS = "failed_to_be_cooked"


class Recipy(ConfigMixin):
    """Основной класс рецепта, содержит все действия по приготовлению блюда"""

    def __init__(self):
        # is_cut_station_free по умолчанию значение False.
        # Меняется на False:
        # - лопатка приезжает в станцию нарезки
        # - поливаем соусом
        # - нарезаем п-ф
        self.is_cut_station_free = asyncio.Event()
        self.time_limit = None

    # методы в части RA
    async def get_move_chain_duration(self, place_to):
        """ Метод получает варианты длительности передвижения, выбирает тот, который
        удовлетвоаряет условиям
        :param place_to: str
        :return: int
        """
        current_destination = await RA.get_current_position()
        forward_destination = place_to
        possible_duration = await RA.get_position_move_time(current_destination, forward_destination)
        if possible_duration:
            return min(possible_duration)
        else:
            raise RAError

    @staticmethod
    async def get_atomic_chain_duration(atomic_info):
        """ Этот метод получает длительность группы атомарных действий в сек
        :param atomic_info:
        :return:
        """
        duration = await RA.get_atomic_action_time(**atomic_info)
        if not duration:
            raise RAError
        return duration

    async def atomic_chain_execute(self, atomic_params_dict):
        """Этот метод выполняет группу атомарных действий
        :param atomic_params_dict: dict с параметрами (name, place)"""
        duration = await self.get_atomic_chain_duration(atomic_params_dict)
        if self.status != self.STOP_STATUS:
            try:
                await RA.atomic_action(**atomic_params_dict)
                print("Успешно выполнили атомарное действие", atomic_params_dict["name"])
            except RAError:
                self.status = self.STOP_STATUS
                print("Ошибка атомарного действия")

    async def move_to_object(self, move_params):
        """Эта функция описывает движение до определенного места.
        :param: tuple (place: uuid, limit: bool)
        limit - это флаг для выбора времени на перемещения.
        RA одно и тоже движение может выполнить за разное время: мин возможное и "с танцами"
        сам временной лимит, то есть время, в которое нужно приехать
        в конечную точку содержится в self.time_limit
        Если лимит True, то движение туда запускается по мин времени, а обратно
        в зависимости от оставшегося времени. Если есть свободное, "танцуем с продуктом"
        """
        print("Начинаем чейн движения")
        place_to, limit = move_params
        duration = await self.get_move_chain_duration(place_to)
        is_need_to_dance = False
        try:
            if limit and self.time_limit:
                place_now = await RA.get_current_position()
                # получаем все возможные временные варианты доезда до точки
                delivery_time_options = await RA.get_position_move_time(place_now, place_to)
                time_left = self.time_limit - time.time()
                time_options = list(filter(lambda t: t <= time_left, delivery_time_options))
                if time_options:
                    duration = max(time_options)
                is_need_to_dance = True if time_left > duration else False
                dance_time = time_left - duration
            await RA.position_move(place_to, duration)
            if is_need_to_dance:
                print("начинаем танцевать дополнительно", dance_time, time.time())
                result = await RA.dance_for_time(dance_time)
                if result:
                    print("RBA успешно подъехал к", place_to, time.time())
        except RAError:
            self.status = self.STOP_STATUS

    # controllers
    async def controllers_get_dough(self, *args):
        """отдает команду контролеру получить тесто"""
        print("получаем тесто у контрллеров")
        dough_point = self.dough.halfstuff_cell
        chain_result = await Controllers.give_dough(dough_point)
        if chain_result:
            print("взяли тесто у контроллеров")
        else:
            print("Ошибка получения теста у контроллеров")
            self.status = self.STOP_STATUS
        # запускает метод списать п\ф
        print("СТАТУС блюда после получения теста", self.status)

    async def controllers_give_sauce(self):
        """Вызов метода контроллеров для поливания соусом"""
        print("Начинаем поливать соусом", time.time())
        self.is_cut_station_free.clear()
        recipe = self.sauce.sauce_cell
        result = await Controllers.give_sauce(recipe)
        if result:
            print("успешно полили соусом")
            self.is_cut_station_free.set()
        else:
            print("---!!! Не успешно полили соусом")
            self.status = self.STOP_STATUS
        print("СТАТУС блюда после поливки соусом", self.status)

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

    async def controllers_cut_half_staff(self, cutting_program):
        print("Начинаем этап ПОРЕЖЬ продукт", time.time())
        duration = cutting_program["duration"]
        program_id = cutting_program["program_id"]
        print("Время начала нарезки п\ф", time.time())
        result = await Controllers.cut_the_product(program_id)
        if result:
            print("успешно нарезали п\ф", time.time())
            self.is_cut_station_free.set()
            self.time_limit = None
            print("СНЯТ временой ЛИМИТ в", time.time())
        else:
            print("---!!! Не успешно нарезали п\ф")
            self.status = self.STOP_STATUS
        print("СТАТУС блюда в нарезке", self.status)

    async def controllers_give_paper(self):
        print("Контроллеры начинают выдавать бумагу", time.time())
        result = await Controllers.give_paper()
        if result:
            pass
        else:
            print("Неудача с бумагой")
            # расписать какая ошибка: - замятие бумаги или полная поломка
            # если замятие, добавить вызов RA на уборку бумаги

    # low-level PBM
    async def chain_execute(self, chain_list):
        """Метод, вызывающий выполнение чейнов из списка
        Чейн - это какая то непрерывная последовательность действий.
        """
        try:
            for chain in chain_list:
                if self.status != self.STOP_STATUS:
                    chain, params = chain
                    await chain(params)
                else:
                    break
        except RAError:
            self.status = self.STOP_STATUS
            print("Ошибка века")

    @staticmethod
    async def is_need_to_change_gripper(current_gripper: str, required_gripper: str):
        """метод проверяет нужно ли менять захват RA
        """
        if str(current_gripper) != required_gripper:
            return True
        return False

    async def change_gripper(self, required_gripper: str):
        """метод, запускающий смену захвата """
        current_gripper = await RA.get_current_gripper()
        is_need_to_change_gripper = await self.is_need_to_change_gripper(current_gripper, required_gripper)
        print("Проверяем, нужно ли менять захват", is_need_to_change_gripper)
        if is_need_to_change_gripper:
            await self.move_to_object((self.CAPTURE_STATION, None))
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
        """Этот метод запускает группу атомарных действий RA по захвату лопатки из печи"""
        oven = self.oven_unit
        atomic_params = {"name": "get_vane_from_oven",
                          "place": oven}
        await self.atomic_chain_execute(atomic_params)

    async def set_vane_in_oven(self, *args):
        """Этот метод запускает группу атомарных действий RA по размещению лопатки в печи"""
        oven_id = self.oven_unit
        atomic_params = {"name": "set_shovel",
                          "place": oven_id}
        for arg in args:
            if arg == "heating":
                asyncio.create_task(self.controllers_turn_heating_on())
        await self.atomic_chain_execute(atomic_params)

    async def control_dough_position(self, *args):
        """отдаем команду на поправление теста"""
        atomic_params = {"name": "get_dough",
                         "place": self.dough.halfstuff_cell}
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

    async def put_half_staff_in_cut_station(self, *args):
        """Этот метод опускает п-ф в станцию нарезки"""
        print("Начинаем размещать продукт в станции нарезки", time.time())
        print("Станция нарезки свободна", self.is_cut_station_free.is_set())
        atomic_params = {
            "name":"set_product",
            "place": self.SLICING
        }
        while not self.is_cut_station_free.is_set() and self.status != "failed_to_be_cooked":
            print("Танцуем с продуктом")
            await asyncio.sleep(1)
            # добавить вызов RA танец с продуктом
        await self.atomic_chain_execute(atomic_params)

    async def dish_packaging(self):
        """Этот метод запускает группу атомарных действий по упаковке пиццы"""
        print("Начинаем упаковывать блюдо RA", time.time())
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

    # средняя укрупненность, так как операция с лимитом по времени от контроллеров
    async def bring_half_staff(self, cell_location_tuple, *args):
        print("Начинаем везти продукт")
        print(cell_location_tuple)
        cell_location, half_staff_position = cell_location_tuple
        atomic_params = {"name": "get_product",
                         "place": "fridge",
                         "obj": "onion",
                         "cell": cell_location,
                         "position": half_staff_position,
        }

        move_params = (cell_location, False)
        move_params_new = (self.SLICING, True)

        what_to_do = [
            (self.move_to_object, move_params),
            (self.atomic_chain_execute, atomic_params),
            (self.move_to_object, move_params_new),
        ]
        await self.chain_execute(what_to_do)
        print("*!*!*!*! Закончили с ингредиентом начинки", self.status, time.time())

    # методы рецепта
    async def chain_get_dough_and_sauce(self, *args):
        """Метод рецепта, описываюший этап возьи тесто и полей соусом"""
        print("Начинается chain Возьми ТЕСТО", time.time())
        self.status = "cooking"
        chain_list = [(self.change_gripper, "None"),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.get_vane_from_oven, None),
                      (self.move_to_object, (self.SLICING, None)),
                      (self.controllers_get_dough, None),
                      (self.control_dough_position, None),
                      (self.move_to_object, (self.SLICING, None)),
                      (self.leave_vane_in_cut_station, None),
                      ]
        await self.chain_execute(chain_list)
        print("Закончили с ТЕСТОМ",time.time(), self.status)
        if self.status != "failed_to_be_cooked":
            asyncio.create_task(self.controllers_give_sauce())
            print("Запустили политие соусом в очередь", time.time())
        print("СТАТУС блюда после теста", self.status, time.time())

    async def get_filling_chain(self, *args):
        """Чейн по доставке и нарезки 1 п\ф"""
        print("% % % Начинаем чейн НАЧИНКИ", time.time())
        (filling_item, cutting_program, storage_adress) = args[0]
        chain_list = [(self.change_gripper, "product"),
                      (self.bring_half_staff, storage_adress),
                      (self.put_half_staff_in_cut_station, None),
        ]
        await self.chain_execute(chain_list)
        if self.status != "failed_to_be_cooked":
            self.time_limit = time.time() + cutting_program["duration"]
            self.is_cut_station_free.clear()
            asyncio.create_task(self.controllers_cut_half_staff(cutting_program))
        print("СТАТУС блюда после начинки",self.status)

    async def bring_vane_to_oven(self, *args):
        print("Начинаем чейн Вези лопатку в печь")
        chain_list = [(self.change_gripper, "None"),
                     (self.move_to_object, (self.SLICING, None)),
                     (self.take_vane_from_cut_station, None),
                     (self.move_to_object, (self.oven_unit, None)),
                     (self.set_vane_in_oven, "heating"),
                     ]
        print("СТАНЦИЯ НАРЕЗКИ СВОБОДНА", self.is_cut_station_free.is_set())
        while not self.is_cut_station_free.is_set():
            try:
                first_task_to_do = args[1].high_priority_queue.get_nowait()
            except asyncio.QueueEmpty:
                print("Доставлять нечего, поработаем в другом месте")
            try:
                task_to_do = args[1].low_priority_queue.get_nowait()
            except asyncio.QueueEmpty:
                print("Мыть ничего не нужно, тоска")
            print("Танцеуем")
            await RA.dance()

        # asyncio.create_task(self.controllers_turn_heating_on())
        await self.chain_execute(chain_list)
        print("Оставили лопатку в печи", time.time())
        if self.status != "failed_to_be_cooked":
            asyncio.create_task(self.controllers_bake())
        print("ЗАКОНЧИЛИ С БЛЮДОМ", time.time())
        print("СТАТУС блюда после доставки лопатки в печь", self.status)

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
        while operation_result.done():
            self.is_dish_ready.set()
            print("БЛЮДО ГОТОВО")
            self.status = "ready"
            print("Это результат установки", self.is_dish_ready.is_set())
            await self.set_oven_timer()
        await asyncio.sleep(0)

    async def set_oven_timer(self, *args):
        print("!!!!!!!!!!ставим таймер на печь", time.time())
        oven_future = asyncio.get_running_loop().create_future()
        self.oven_future = oven_future
        self.oven_unit.dish_waiting_time = time.time() + OVEN_FREE_WAITING_TIME
        await asyncio.create_task(self.oven_timer())

    async def oven_timer(self, *args):
        """args пустые"""
        print("!!!!!!!!!!!!Начинаем ждать первый интервал", time.time())
        print("Статус печи", self.oven_unit.status)
        self.oven_unit.status = "waiting_15"
        await asyncio.sleep(OVEN_FREE_WAITING_TIME)
        print("!!!!!!!!!!! время первого сна завершено",time.time())
        if not self.oven_future.cancelled():
            print("!!!!!!!!!!!!!!блюдо не забрали, запускаем 60 сек")
            self.oven_unit.status = "waiting_60"
            self.oven_unit.dish_waiting_time = time.time() + OVEN_LIQUIDATION_TIME
            await asyncio.sleep(OVEN_LIQUIDATION_TIME)
            if not self.oven_future.cancelled():
                print("!!!!!!!!!!!!!!блюдо не забрали, запускаем чистку")
                self.oven_future.set_result("time is over")
                self.oven_unit.status = "cleaning"
                await args[1].high_priority_queue.put_nowait()
                self.status = self.STOP_STATUS

    async def time_changes_handler(self, time_futura,  *args):
        """Обрабатывает результаты футуры об изменении времени выпечки"""
        print("ОБРАБАТЫВАЕМ ФУТУРУ")
        print(" Это ффутура из time_change_handler",self.time_changes_event)
        lock = asyncio.Lock()
        async with lock:
            self.time_changes_event["result"] = time_futura
            self.time_changes_event["event"].set()

    def create_dish_recipe(self):
        """создает рецепт блюда"""
        dish_recipe = [self.chain_get_dough_and_sauce]
        for filling_item in self.filling.filling_content:
            print(filling_item)
            dish_recipe.append((self.get_filling_chain, filling_item))
        dish_recipe.append(self.bring_vane_to_oven)
        return dish_recipe

    async def make_crust(self):
        print("Начинаем разогрев пиццы")
        oven_mode = "make_crust"
        recipe = self.make_crust_program
        time_changes = asyncio.get_running_loop().create_future()
        await self.time_changes_handler(time_changes)
        operation_results = await Controllers.start_baking(self.oven_unit.oven_id, oven_mode, recipe, time_changes)
        return operation_results

    async def create_dish_delivery_recipe(self):
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

# да, тут пока вообще помойка, нужен мощный рефакторинг
# не сделано