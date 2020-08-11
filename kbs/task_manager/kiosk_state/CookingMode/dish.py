"""Тут описывается блюдо в заказе"""

import asyncio
import time

from .recipe.dish_recipe import DishRecipe
from kbs.ra_api.RA import RA, RAError
from kbs.data.kiosk_modes.cooking_mode import Status, CookingModeConst
from kbs.exceptions import ControllersFailedError


class DishStatus(object):
    """
    Расшифровка статусов блюда:
    - received: блюдо получено, ждет в очереди
    - cooking: лопатка достана из печи, идет готовка на любой стадии
    - baking: пицца находится в печи на выпечке
    - ready: пицца выпечена
    - packing: начата упаковка
    - failed_to_be_cooked: боюдо не приготовлено
    - packed: блюдо упаковано
    - time_is_up: блюдо не забрали, выбрашено
    """

    DISH_STATUSES = ["received", "cooking", "baking", "failed_to_be_cooked", "ready",
                     "packed", "time_is_up"]

    def __init__(self, time_changes_event):
        self.status = "received"
        self.is_dish_ready = None
        self.time_changes_event = time_changes_event

    @property
    def is_dish_failed(self):
        """Этот метод проверяет можно ли готовить блюдо дальше, то есть
         его статус не STOP_STATUS """
        return True if self.status == Status.STOP_STATUS else False

    async def mark_dish_as_failed(self):
        """Этот метод помечает блюдо как законченное для готовки, но неудачно"""

        self.status = Status.STOP_STATUS
        self.is_dish_ready.set()

    async def time_changes_handler(self, time_future):
        """Обрабатывает результаты футуры об изменении времени выпечки"""
        print("ОБРАБАТЫВАЕМ ФУТУРУ")
        print(" Это ффутура из time_change_handler", self.time_changes_event)
        lock = asyncio.Lock()
        async with lock:
            self.time_changes_event["result"] = time_future
            self.time_changes_event["event"].set()


class Dish(DishStatus, DishRecipe):
    """Этот класс описывает блюдо в заказе"""

    def __init__(self, time_changes_event, dish_id, dish_data, order_ref_id, free_oven_object):
        super().__init__(time_changes_event)

        self.id = dish_id
        self.order_ref_id = order_ref_id
        self.is_last_dish_in_order = False

        # распаковываем данные о том, из чего состоит блюдо
        self.dough = BaseDough(dish_data["dough"])
        self.sauce = BaseSauce(dish_data["sauce"])
        self.filling = BaseFilling(dish_data["filling"])
        self.additive = BaseAdditive(dish_data["additive"])

        self.oven_unit = free_oven_object
        self.oven_recipes = self.fill_oven_recipes(dish_data)
        self.cooking_recipe = self.create_dish_recipe()
        # self.delivery_chain_list = self.create_dish_delivery_recipe()
        # self.throwing_away_chain_list = self.throwing_dish_away()

        # у каждой ячейки выдачи есть 2 "лотка", нужно распределить в какой лоток помещает блюдо
        self.pickup_point_unit: int

    @staticmethod
    def fill_oven_recipes(dish_data):
        oven_recipes = {
            "cooking_program": dish_data["filling"]["cooking_program"],
            "make_crust_program": dish_data["filling"]["make_crust_program"],
            "pre_heating_program": dish_data["filling"]["pre_heating_program"],
        }
        return oven_recipes

    async def half_staff_cell_evaluation(self):
        """Этот метод назначает п-ф из БД"""
        # не сделано
        pass

    async def mark_dish_as_started_cooking(self):
        """ Этот метод помечяет, что начата готовка блюда """

        lock = asyncio.Lock()
        async with lock:
            self.status = "cooking"
            self.oven_unit.status = "occupied"

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

        await self.mark_dish_as_started_cooking()
        await self.chain_execute(to_do, equipment)

        print(f"PBM {time.time()} - Закончили с ТЕСТОМ, статус блюда {self.status}")
        print()

        if not self.is_dish_failed:
            sauce_recipe = self.sauce.sauce_cell
            duration = self.sauce.sauce_recipe["duration"]
            asyncio.create_task(self.give_sauce(sauce_recipe, duration, equipment))

    async def turn_on_oven_heating(self, storage_address, equipment,
                                   cutting_program, is_ready_for_baking):

        additive_time = self.additive.duration

        time_before_baking = await self.time_calculation(storage_address,
                                                         equipment,
                                                         cutting_program,
                                                         additive_time,
                                                         self.oven_unit.oven_id)

        time_gap_to_heating = time_before_baking - CookingModeConst.OVEN_HEATING_DURATION

        print(f"PBM {time.time()} - Запустили прогрев")
        heating_task = asyncio.create_task(self.controllers_turn_heating_on(self, time_gap_to_heating,
                                                                            is_ready_for_baking))

    async def prepare_filling_item(self, *args):
        """Чейн по доставке и нарезки 1 п-ф
        args: (params, equipment)

        """
        # print("Это аргс из начинки", args)
        filling_data, equipment = args

        filling_item, cutting_program, storage_address, is_last_item = \
            await self.unpack_filling_data(filling_data)

        to_do = (
            (self.change_gripper, "product"),
            (self.bring_half_staff, storage_address),
            (self.put_half_staff_in_cut_station, None),
        )

        await asyncio.sleep(0.2)
        print(f"PBM - {time.time()} Начинаем готовить {filling_item.upper()}")

        is_ready_for_baking = asyncio.Event()

        if is_last_item:
            await asyncio.sleep(0.1)

            await self.turn_on_oven_heating(storage_address,
                                            equipment,
                                            cutting_program,
                                            is_ready_for_baking)

        await self.chain_execute(to_do, equipment)

        if not self.is_dish_failed:
            asyncio.create_task(self.cut_half_staff(cutting_program,
                                                    equipment,
                                                    self,
                                                    is_last_item))
            print(f"PBM {time.time()} - Запустили нарезку п-ф в очередь")
            print()

            if is_last_item:
                await self.change_gripper("None", equipment)
                await self.start_baking(None, equipment, is_ready_for_baking)

    async def start_baking(self, *args):
        """Этот метод транспортрует лопатку в печь и запускает выпечку"""
        print("Начинаем чейн Вези лопатку в печь")
        # print("Это аргс из начинки", args)
        _, equipment, is_ready_for_baking = args

        chain_list = [(self.move_to_object, (self.SLICING, None)),
                      (self.take_vane_from_cut_station, None),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.set_vane_in_oven, "heating"),
                      ]

        print("СТАНЦИЯ НАРЕЗКИ СВОБОДНА", equipment.cut_station.is_free.is_set())
        while not equipment.cut_station.is_free.is_set():
            print("Танцеуем")
            await RA.dance()

        await self.chain_execute(chain_list, equipment)
        print("Оставили лопатку в печи", time.time())
        self.status = "baking"
        is_ready_for_baking.set()

    def create_dish_recipe(self):
        """Этот метод создает рецепт для блюда"""
        print("начинаем создавать рецепт")
        dish_recipe = [self.prepare_dough_and_sauce]
        for filling_item in self.filling.filling_content:
            dish_recipe.append((self.prepare_filling_item, filling_item))
        return dish_recipe

    async def chain_execute(self, chain_list, equipment):
        """Метод, вызывающий выполнение чейнов из списка
        Чейн - это какая то непрерывная последовательность действий.
        """
        try:
            for chain in chain_list:
                if not self.is_dish_failed:
                    chain, params = chain
                    await chain(params, equipment, self)
                else:
                    break
        except (RAError, ControllersFailedError):
            print("Ошибка века")
            await self.mark_dish_as_failed()

    def __repr__(self):
        return f"Блюдо {self.id} состоит из {self.dough}, {self.sauce}, {self.filling}, {self.additive}  " \
               f"\"Зарезервирована печь\" {self.oven_unit} Статус {self.status}"


class BasePizzaPart(object):
    """Базовый класс компонента пиццы"""

    def cell_evaluation(self):
        """Это метод обращается к БД, находит где лежит нужный п-ф"""
        # не сделано
        pass


class BaseDough(BasePizzaPart):
    """Этот класс содержит информацию о тесте, которое используется в заказанном блюде"""

    def __init__(self, dough_data):
        self.halfstuff_id = dough_data["id"]
        self.halfstuff_cell = 21
        self.recipe_data = dough_data["recipe"]

    def __repr__(self):
        return f"Тесто {self.halfstuff_id}"


class BaseSauce(BasePizzaPart):
    """Этот класс содержит инфорамцию об используемом соусе"""

    def __init__(self, sauce_data):
        self.sauce_id = sauce_data["id"]
        self.sauce_content = sauce_data["content"]
        self.sauce_recipe = sauce_data["recipe"]
        # sauce_cell=[(1, 1), (2, 2)] 0 - id насосной станции, 1 - программа запуска
        self.sauce_cell = self.unpack_data(sauce_data)

    def unpack_data(self, sauce_data):
        """выводт данные в виде [(cell_id, program_id), (None, 3)]"""
        # переписать, временно

        a = sauce_data["recipe"]["content"]
        for_controllers = [(a[i]["sauce_station"], a[i]["program"]) for i in a]
        return for_controllers

    def __repr__(self):
        return f"Соус {self.sauce_id}"


class BaseFilling(object):
    """Этот класс содержит информацию о начинке.
    filling_data["content"] содержит кортеж словарей
    Вложенный словарь содержит информцию об id_пф и словарь для нарезки
    (halfstaff_id, {"cutting_program_id":str, "duration": int})
    """

    def __init__(self, filling_data):
        self.filling_id = filling_data["id"]
        self.filling_content = filling_data["content"]
        self.cell_data_unpack()

    def cell_data_unpack(self):
        """Это метод - загрушка, который как бы получает данные о местах хранения п-ф в начинке
        # не сделано

        Элемент списка начинки выглядит вот так, последний элемент - это место хранения
        [tomato, {'program_id': 2, 'duration': 10}, ('d4', (3, 4))]"""
        # место хранения в холодильнике
        input_data = (
            ("d4", (3, 4)), ("a4", (3, 4)), ("t4", (3, 4)),
            ("b4", (1, 1)), ("a4", (1, 1)), ("c4", (2, 1))
        )

        self.filling_content = [item + [value] for item, value in zip(self.filling_content, input_data)]

        content_list = []
        for item in self.filling_content:
            my_dict = {"id": (item)[0], "cut_program": (item)[1], "location": (item)[2], "is_last": False}
            content_list.append(my_dict)
        self.filling_content = content_list
        self.filling_content[-1]["is_last"] = True

    def __repr__(self):
        return f"Начинка {self.filling_id}"


class BaseAdditive(BasePizzaPart):
    """Этот класс описывает добавку"""

    def __init__(self, additive_data):
        self.halfstuff_id = additive_data["id"]
        self.halfstuff_cell = None
        self.duration = additive_data["recipe"]["duration"]

    def __repr__(self):
        return f"Добавка {self.halfstuff_id}"
