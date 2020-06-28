import asyncio
import time

from .recipe_class import Recipy


class BaseOrder(object):
    """Этот класс представляет шаблон заказа, формируемого в среде окружения для каждого полученного заказа
    """
    ORDER_STATUS = ["received", "cooking", "ready", "packed", "wait to delivery", "delivered", "closed",
                    "failed_to_be_cooked", "not_delivered"]

    def __init__(self, new_order, ovens_reserved):

        self.ref_id = new_order["refid"]
        self.dishes = self.dish_creation(new_order["dishes"], ovens_reserved)
        self.status = "received"
        self.pickup_point = None
        self.is_order_ready_monitoring = []

    def dish_creation(self, dishes, ovens_reserved):
        """Creates list of dishes objects in order"""

        self.dishes = [BaseDish(dish_id, dishes[dish_id], ovens_reserved[index])
                       for index, dish_id in enumerate(dishes)]
        return self.dishes

    async def create_is_order_ready_monitoring(self):
        """Этот метод создает мониторинг готовности блюд заказа через asyncio.Event """
        for dish in self.dishes:
            is_dish_ready = asyncio.Event()
            dish.is_dish_ready = is_dish_ready
            self.is_order_ready_monitoring.append(is_dish_ready)
        return self.is_order_ready_monitoring

    async def order_readiness_monitoring(self):
        """Этот метод проверяет, сработали ли события готовности блюд в заказе"""
        while not all(list(map(lambda i: i.is_set(), self.is_order_ready_monitoring))):
            await asyncio.sleep(1)
        print("Сработало событие ЗАКАЗ ГОТОВ", time.time())
        self.status = "ready"
        # записать в БД статус

    def __repr__(self):
        return f"Заказ № {self.ref_id}"


class BaseDish(Recipy):
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

    def __init__(self, dish_id, dish_data, free_oven_id):
        super().__init__()
        self.id = dish_id
        # распаковываем данные о том, из чего состоит блюдо
        self.dough = BaseDough(dish_data["dough"])
        self.sauce = BaseSauce(dish_data["sauce"])
        self.filling = BaseFilling(dish_data["filling"])
        self.additive = BaseAdditive(dish_data["additive"])

        self.oven_unit = free_oven_id
        self.status = "received"
        self.chain_list = self.create_dish_recipe()
        self.delivery_chain_list = self.create_dish_delivery_recipe()
        self.throwing_away_chain_list = self.throwing_dish_away()
        self.baking_program = dish_data["filling"]["cooking_program"]
        self.make_crust_program = dish_data["filling"]["make_crust_program"]
        self.pre_heating_program = dish_data["filling"]["pre_heating_program"]
        self.stand_by = dish_data["filling"]["stand_by"]
        self.oven_future = None
        # у каждой ячейки выдачи есть 2 "лотка", нужно распределить в какой лоток помещает блюдо
        self.pickup_point_unit: int
        self.is_dish_ready = None

    async def half_staff_cell_evaluation(self):
        """Этот метод назначает п\ф из БД"""
        # не сделано
        pass

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

    def __repr__(self):
        return f"Начинка {self.filling_id}"


class BaseAdditive(BasePizzaPart):
    """Этот класс описывает добавку"""

    def __init__(self, additive_data):
        self.halfstuff_id = additive_data["id"]
        self.halfstuff_cell = None

    def __repr__(self):
        return f"Добавка {self.halfstuff_id}"
