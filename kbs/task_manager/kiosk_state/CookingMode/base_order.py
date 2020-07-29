import asyncio
import time

from .recipe_class import DishRecipe
from kbs.data.kiosk_modes.cooking_mode import CookingModeConst


class Order(object):
    """Этот класс содержит информцию о заказе.
    self.check_code: str

    self.dishes: list вида [экземпляр_1_класса_Dish, экземпляр_2_класса_Dish]

    # переделать на константы
    self.status: str

    self.is_

    """

    ORDER_STATUS = ["received", "cooking", "ready", "packed", "wait to delivery", "delivered", "closed",
                    "failed_to_be_cooked", "not_delivered"]

    def __init__(self, new_order_content, ovens_reserved, time_changes_event):

        self.check_code = new_order_content["check_code"]
        self.dishes = self.dish_creation(new_order_content["dishes"], ovens_reserved, time_changes_event)
        self.status = "received"
        # перенести в блюдо
        self.pickup_point = None
        self.dish_readiness_events = []
        self.delivery_request_event = asyncio.Event()

    def dish_creation(self, dishes, ovens_reserved, time_changes_event):
        """Creates list of dishes objects in order

        :param dishes: dict вида {dish_id: {добавить словарь}}
        :param ovens_reserved: list вида [экземпляр_класса_OvenUnit]
        :param time_changes_event: dict вида {"event": asyncio.Event(), "result": None}

        """

        self.dishes = [BaseDish(dish_id, dishes[dish_id], ovens_reserved[index], time_changes_event,
                                self.check_code) for index, dish_id in enumerate(dishes)]
        return self.dishes

    async def order_marker(self):
        """Этот метод маркирует заказ в зависимости от кол-ва блюд в нем """
        if len(self.dishes) > 1:
            self.dishes[-1].one_dish_order = True
        else:
            self.dishes[0].one_dish_order = True

    async def set_waiting_timer(self):
        print("Начинаем ждать выдачу блюда, 1", time.time())
        stop_time = time.time() + CookingModeConst.OVEN_FREE_WAITING_TIME
        while time.time() < stop_time:
            if not self.delivery_request_event.is_set():
                await asyncio.sleep(1)
                print("Ждем 1 интервал")
            else:
                print("Блюдо запрошено к доставке")
                break
        if not self.delivery_request_event.is_set():
            print("Закончили ждать 1 интервал", time.time())
            for dish in self.dishes:
                dish.oven_unit.status = "waiting_60"
            stop_time = time.time() + CookingModeConst.OVEN_FREE_WAITING_TIME*2
            while not self.delivery_request_event.is_set() and time.time() < stop_time:
                print("Ждем 2 интервал")
                await asyncio.sleep(1)
            print("ТАЙМЕР закончился, блюдо выкидываем")
        else:
            pass

    async def create_is_order_ready_monitoring(self):
        """Этот метод создает мониторинг готовности блюд заказа через asyncio.Event """
        for dish in self.dishes:
            is_dish_ready_event = asyncio.Event()
            dish.is_dish_ready = is_dish_ready_event
            self.dish_readiness_events.append(is_dish_ready_event)
        return self.dish_readiness_events

    async def order_readiness_monitoring(self):
        """Этот метод проверяет, сработали ли события готовности блюд в заказе"""
        while not all(list(map(lambda i: i.is_set(), self.dish_readiness_events))):
            await asyncio.sleep(1)
        print("Сработало событие ЗАКАЗ ГОТОВ", time.time())
        print(list(map((lambda i: i.status == "failed_to_be_cooked"), self.dishes)))

        await self.change_order_status()
        print("Это статус ЗАКАЗА", self.status)
        await self.set_waiting_timer()
        # записать в БД статус

    async def change_order_status(self):
        if all(list(map((lambda i: i.status == "failed_to_be_cooked"), self.dishes))):
            self.status = "failed_to_be_cooked"
        elif any(list(map((lambda i: i.status == "failed_to_be_cooked"), self.dishes))):
            self.status = "partially_ready"
        else:
            self.status = "ready"

    def __repr__(self):
        return f"Заказ № {self.check_code}"


class BaseDish(DishRecipe):
    """Этот класс представляет собой шаблон блюда в заказе.
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
    STOP_STATUS = "failed_to_be_cooked"

    def __init__(self, dish_id, dish_data, free_oven_object, time_changes_event, order_ref_id):
        super().__init__()
        self.id = dish_id
        self.order_ref_id = order_ref_id
        self.one_dish_order = False
        # распаковываем данные о том, из чего состоит блюдо
        self.dough = BaseDough(dish_data["dough"])
        self.sauce = BaseSauce(dish_data["sauce"])
        self.filling = BaseFilling(dish_data["filling"])
        self.additive = BaseAdditive(dish_data["additive"])

        self.oven_unit = free_oven_object
        self.status = "received"
        self.cooking_recipe = self.create_dish_recipe()
        # self.delivery_chain_list = self.create_dish_delivery_recipe()
        # self.throwing_away_chain_list = self.throwing_dish_away()
        self.baking_program = dish_data["filling"]["cooking_program"]
        self.make_crust_program = dish_data["filling"]["make_crust_program"]
        self.pre_heating_program = dish_data["filling"]["pre_heating_program"]
        self.stand_by = dish_data["filling"]["stand_by"]
        # у каждой ячейки выдачи есть 2 "лотка", нужно распределить в какой лоток помещает блюдо
        self.pickup_point_unit: int
        self.is_dish_ready = None
        self.time_changes_event = time_changes_event

    @property
    def is_dish_failed(self):
        return True if self.status == self.STOP_STATUS else False

    async def half_staff_cell_evaluation(self):
        """Этот метод назначает п\ф из БД"""
        # не сделано
        pass

    def create_dish_recipe(self):
        """Этот метод создает рецепт для блюда"""
        print("начинаем создавать рецепт")
        dish_recipe = [self.prepare_dough_and_sauce]
        for filling_item in self.filling.filling_content:
            dish_recipe.append((self.prepare_filling_item, filling_item))
        dish_recipe.append(self.start_baking)
        return dish_recipe

    async def mark_dish_as_failed(self):
        self.status = self.STOP_STATUS
        self.is_dish_ready.set()

    async def time_changes_handler(self, time_futura, *args):
        """Обрабатывает результаты футуры об изменении времени выпечки"""
        print("ОБРАБАТЫВАЕМ ФУТУРУ")
        print(" Это ффутура из time_change_handler", self.time_changes_event)
        lock = asyncio.Lock()
        async with lock:
            self.time_changes_event["result"] = time_futura
            self.time_changes_event["event"].set()

    async def mark_dish_as_started(self):
        """ """
        self.status = "cooking"
        self.oven_unit.status = "occupied"

    def __repr__(self):
        return f"Блюдо {self.id} состоит из {self.dough}, {self.sauce}, {self.filling}, {self.additive}  " \
               f"\"Зарезервирована печь\" {self.oven_unit} Статус {self.status}"


class BasePizzaPart(object):
    """Базовый класс компонента пиццы"""

    def cell_evaluation(self):
        """Это метод обращается к БД, находит где лежит нужный п\ф"""
        # не сделано
        pass


class BaseDough(BasePizzaPart):
    """Этот класс содержит информацию о тесте, которое используется в заказанном блюде"""

    def __init__(self, dough_data):
        self.halfstuff_id = dough_data["id"]
        # self.halfstuff_cell хранит только место ячейки, при инициации None
        self.halfstuff_cell = 21
        self.recipe_data = dough_data["recipe"]

    def __repr__(self):
        return f"Тесто {self.halfstuff_id}"


class BaseSauce(BasePizzaPart):
    """Этот класс содержит инфорамцию об используемом соусе"""

    def __init__(self, sauce_data):
        self.sauce_id = sauce_data["id"]
        self.sauce_content = sauce_data["content"]
        # sauce_cell=[(1, 1), (2, 2)] 0 - id насосной станции, 1 - программа запуска
        self.sauce_cell = self.unpack_data(sauce_data)
        self.sauce_recipe = sauce_data["recipe"]

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
        """Это метод - загрушка, который как бы получает данные о местах хранения п\ф в начинке
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
            my_dict = {}
            my_dict["id"], my_dict["cut_program"], my_dict["location"] = item
            my_dict["is_last"] = False
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

    def __repr__(self):
        return f"Добавка {self.halfstuff_id}"
