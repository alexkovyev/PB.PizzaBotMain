import asyncio
import concurrent.futures
import multiprocessing
import time

from functools import partial

from .BaseOrder import BaseOrder
from .CookingModeErrors import OvenReserveFailed
from config.config import COOKINGMODE
from config.recipe_data import recipe_data
from controllers.ControllerBus import Controllers
from kiosk_state.BaseMode import BaseMode
from RA.RA import RA
from .recipe_class import Recipy
from server.custom_errors import OvenReservationError


class BeforeCooking(BaseMode):

    def __init__(self):
        super().__init__()

    @classmethod
    def start_testing(clx, equipment_data):
        """Тут вызываем методы контролеров по тестированию оборудования"""
        # вызывается какой то супер метод контроллеров на проверку,
        # возвращает status и dict с данными об оборудовании
        # не сделано, заглушка
        is_equipment_ok = True
        print("Начинаем тестировать оборудования", time.time())
        time.sleep(4)
        print("Оборудование протестировано, исправно", time.time())
        return is_equipment_ok, equipment_data

    @classmethod
    def parse_recipes(clx):
        """Парсит все рецепты в директории и возвращает словарь вида:
        не сделано, заглушка
        """
        print("Начинаем парсить рецепты", time.time())
        time.sleep(4)
        print("Рецепты спарсены", time.time())
        recipes = recipe_data
        return recipes

    @classmethod
    async def start_pbm(clx, equipment_data):
        """Этот метод запускает режим готовки. Так как это блокирующие операции,
        используется run_in_executor"""
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        my_loop = asyncio.get_running_loop()

        async def task_1(equipment_data):
            is_equipment_ok, equipment_data = await my_loop.run_in_executor(pool,
                                                                            partial(clx.start_testing,
                                                                                    equipment_data))
            return is_equipment_ok, equipment_data

        async def task_2():
            recipes = await my_loop.run_in_executor(pool, clx.parse_recipes)
            return recipes

        task_1 = my_loop.create_task(task_1(equipment_data))
        task_2 = my_loop.create_task(task_2())
        my_result = await asyncio.gather(task_1, task_2)
        return my_result


class CookingMode(BaseMode):
    """Это основной режим готовки
    self.recipes - это словарь, содержащий спарсенные данные рецепта

    self.equipment - это текщий экземпляр класса Equipment

    self.current_orders_proceed - это словарь, содержащий все заказы за текущий сеанс работы

    self.orders_requested_for_delivery - это словарь, содержащий все заказы, по которым поучатель
                                         просканировал qr код
    """

    STOP_STATUS = "failed_to_be_cooked"

    def __init__(self, recipes, equipment):
        super().__init__()
        self.recipes = recipes
        self.equipment = equipment
        self.current_orders_proceed = {}
        self.orders_requested_for_delivery = {}
        self.oven_time_changes_event = {"event": asyncio.Event(), "result": None}
        # разные полезные очереди по приоритету
        self.main_queue = asyncio.Queue()
        self.high_priority_queue = asyncio.Queue()
        self.low_priority_queue = asyncio.Queue()

    @property
    def is_downtime(self):
        """Проверяет можно ли танцеать, те все очереди пустые"""
        return all(map(lambda p: p.empty(),
                       (self.main_queue, self.low_priority_queue, self.high_priority_queue)))

    async def checking_order_for_double(self, new_order_id):
        """Этот метод проверяет есть ли уже заказ с таким ref id в обработке
        :param new_order_id: str
        :return bool"""
        return True if new_order_id not in self.current_orders_proceed else False

    async def get_order_content_from_db(self, new_order_id):
        """Этот метод вызывает процедуру 'Получи состав блюд в заказе' и возвращает словарь вида
        {"refid": new_order_id,
                     "dishes": {"40576654-9f31-11ea-bb37-0242ac130002":
                         {
                             "dough": {"id": 2},
                             "sauce": {"id": 2, "content": ((1, 5), (2, 25))},
                             "filling": {"id": 1, "content": (6, 2, 3, 3, 6, 8)},
                             "additive": {"id": 7}
                         }
                         ,
                         "6327ade2-9f31-11ea-bb37-0242ac130002":
                             {
                                 "dough": {"id": 1},
                                 "sauce": {"id": 2, "content": ((1, 5), (2, 25))},
                                 "filling": {"id": 1, "content": (6, 2, 3, 3, 6, 8)},
                                 "additive": {"id": 1}
                             }
                     }
                     }

        Это метод - заглушка, так как БД пока нет
        """
        new_order = dict(refid=new_order_id, dishes={"40576654-9f31-11ea-bb37-0242ac130002":
            {
                "dough": {"id": 2},
                "sauce": {"id": 2, "content": ((1, 5), (2, 25))},
                "filling": {"id": 1, "content": ("tomato", "cheese", "ham", "olive", "pepper", "bacon")},
                "additive": {"id": 7}
            },
            "6327ade2-9f31-11ea-bb37-0242ac130002":
                {
                    "dough": {"id": 1},
                    "sauce": {"id": 2, "content": ((1, 5), (2, 25))},
                    "filling": {"id": 1, "content": ("tomato", "cheese", "ham", "olive", "pepper", "bacon")},
                    "additive": {"id": 1}
                }
        })
        return new_order

    async def get_recipe_data(self, new_order):
        """Этот метод добавляет в данные о блюде параметры чейнов рецепта для конкретного ингредиента
        :param словарь блюд из заказа
        {'40576654-9f31-11ea-bb37-0242ac130002':
            {'dough': {'id': 2},
            'sauce': {'id': 2, 'content': ((1, 5), (2, 25))},
            'filling': {'id': 1, 'content': (6, 2, 3, 3, 6, 8)},
            'additive': {'id': 7}},
        '6327ade2-9f31-11ea-bb37-0242ac130002':
            {'dough': {'id': 1},
            'sauce': {'id': 2, 'content': ((1, 5), (2, 25))},
            'filling': {'id': 1, 'content': (6, 2, 3, 3, 6, 8)},
            'additive': {'id': 1}}}

        Возвращаемый результат, где filling -->content tuple 0 - halfstaff_id, 1 - {cutting_program}
        {'refid': 65, 'dishes': [
        {'dough': {'id': 2, 'recipe': {1: 10, 2: 5, 3: 10, 4: 10, 5: 12, 6: 7, 7: 2}},

        'sauce': {'id': 2,
                 'content': ((1, 5), (2, 25)),
                'recipe':
                        {'duration': 20,
                        'content': {1:
                                     {'program': 1, 'sauce_station': None, 'qt': 5},
                                    2:
                                      {'program': 3, 'sauce_station': None, 'qt': 25}}}},

        'filling': {'id': 1,
        'content': ((6, {'program_id': 2, 'duration': 10}), (2, {'program_id': 1, 'duration': 12}),
        (3, {'program_id': 5, 'duration': 15}), (3, {'program_id': 8, 'duration': 8}),
        (6, {'program_id': 4, 'duration': 17}), (8, {'program_id': 9, 'duration': 9})),
        'cooking_program': (2, 180), 'make_crust_program': (2, 20), 'chain': {}},

        'additive': {'id': 7, 'recipe': {1: 5}}},

        {'dough': {'id': 1, 'recipe': {1: 10, 2: 5, 3: 10, 4: 10, 5: 12, 6: 7, 7: 2}},

        'sauce': {'id': 2,
                 'content': ((1, 5), (2, 25)),
                'recipe':
                        {'duration': 20,
                        'content': {1:
                                     {'program': 1, 'sauce_station': None, 'qt': 5},
                                    2:
                                      {'program': 3, 'sauce_station': None, 'qt': 25}}}},
        'filling': {'id': 1, 'content': ((6, {'program_id': 2, 'duration': 10}),
        (2, {'program_id': 1, 'duration': 12}), (3, {'program_id': 5, 'duration': 15}),
        (3, {'program_id': 8, 'duration': 8}), (6, {'program_id': 4, 'duration': 17}),
        (8, {'program_id': 9, 'duration': 9})),
        'cooking_program': (1, 180), 'make_crust_program': (1, 20), 'chain': {}},

        'additive': {'id': 1, 'recipe': {1: 5}}}]}
"""

        # print("Входные данные", new_order)

        async def create_sauce_recipe(self, dish):
            """Этот метод выбирает рецепт для конкретного компонента соуса из общей базы рецептов"""
            sauce_id = dish["sauce"]["id"]
            dish["sauce"]["recipe"] = self.recipes["sauce"][sauce_id]
            for component, my_tuple in zip(dish["sauce"]["recipe"]["content"], dish["sauce"]["content"]):
                dish["sauce"]["recipe"]["content"][component]["qt"] = my_tuple[1]
            # print("составили рецепт соуса", dish["sauce"])

        async def create_filling_recipe(self, dish):
            """Этот метод выбирает рецепт начинки для начинки в общем
            и для каждого компонента начинки в целом"""
            filling_id = dish["filling"]["id"]
            dough_id = dish["dough"]["id"]
            dish["filling"]["cooking_program"] = self.recipes["filling"][filling_id]["cooking_program"][dough_id]
            dish["filling"]["make_crust_program"] = self.recipes["filling"][filling_id]["make_crust_program"][dough_id]
            dish["filling"]["pre_heating_program"] = self.recipes["filling"][filling_id]["pre_heating_program"][
                dough_id]
            dish["filling"]["stand_by"] = self.recipes["filling"][filling_id]["stand_by_program"][dough_id]
            halfstaff_content = dish["filling"]["content"]
            cutting_program = self.recipes["filling"][filling_id]["cutting_program"]
            dish["filling"]["content"] = [list(_) for _ in (zip(halfstaff_content, cutting_program))]
            print("Составили рецепт начинки", dish["filling"])

        for dish in new_order.values():
            dish["dough"]["recipe"] = self.recipes["dough"]
            await create_sauce_recipe(self, dish)
            await create_filling_recipe(self, dish)
            dish["additive"]["recipe"] = self.recipes["additive"]

    async def reserve_oven(self, new_order):
        """ Этот метод резервирует печи для каждого блюда в заказе
        :param new_order: str
        :param oven_data: объект класса Oven
        :return list of OvenUnit instance selected for the order
        """
        try:
            ovens_reserved = [await self.equipment.ovens.oven_reserve(dish) for dish in new_order["dishes"]]
            return ovens_reserved
        except OvenReservationError:
            raise OvenReserveFailed("Ошибка назначения печей на заказ. Нет свободных печей")

    async def create_new_order(self, new_order):
        """Этот метод создает экземпляр класса Order и заносит его в словарь self.current_orders_proceed
        @:params:
        new_order - это словарь с блюдами, получаемый из БД в рамках метода get_order_content_from_db """

        order_content = await self.get_order_content_from_db(new_order)
        await self.get_recipe_data(order_content["dishes"])
        try:
            ovens_reserved = await self.reserve_oven(order_content)
        except OvenReserveFailed:
            pass
        order = BaseOrder(order_content, ovens_reserved, self.oven_time_changes_event)
        if order:
            # если заказ создан успешно, помещаем его в словарь всех готовящихся заказов
            await order.dish_marker()
            self.current_orders_proceed[order.ref_id] = order
            for dish in order.dishes:
                await dish.half_staff_cell_evaluation()
                await self.put_chains_in_queue(dish, self.main_queue)
            await order.create_is_order_ready_monitoring()
            asyncio.create_task(order.order_readiness_monitoring())

    async def put_chains_in_queue(self, dish, queue):
        """Добавляет чейны рецепта в очередь в виде кортежа (dish, chain)"""
        chains = dish.chain_list
        for chain in chains:
            await queue.put(chain)

    async def unpack_chain_data(self, queue, params=None):
        """Этот метод распаковывает кортеж, проверяет можно ли готовить блюдо
        (те статус блюда не STOP_STATUS) и запускает чейн с параметрами """
        print("Начинаем распаковку")
        chain_to_do = await queue.get()
        if isinstance(chain_to_do, tuple):
            chain_to_do, params = chain_to_do
        if chain_to_do.__self__.status != self.STOP_STATUS:
            print("Готовим блюдо", chain_to_do.__self__.id)
            await chain_to_do(params, self)

    async def run(self):
        """Этот метод обеспечивает вызов методов по приготовлению блюд и другой важной работе"""

        asyncio.create_task(self.time_changes_monitor())
        asyncio.create_task(self.dish_inform_monitor())

        while True:
            print("Работает cooking", time.time())
            if self.is_downtime:
                print("Танцуем, других заданий нет")
                await RA.dance()
            else:
                if not self.high_priority_queue.empty():
                    print("Выдаем заказ")
                    await self.high_priority_queue.get()
                elif not self.main_queue.empty():
                    print("Вернулись в очередь main")
                    await self.unpack_chain_data(self.main_queue)
                elif not self.low_priority_queue.empty():
                    print("Моем или выкидываем пиццу")

    async def dish_inform_monitor(self):
        while True:
            time_list = []
            for oven in self.equipment.ovens.oven_units.values():
                if oven.stop_baking_time is not None and oven.stop_baking_time > (time.time() +10) and \
                        oven.stop_baking_time < (time.time() +11):
                    print("Это время окончания выпечки в печи", oven.stop_baking_time)
                    print(time.time())
                    print("Это блюдо", oven.dish)
                    time_list.append(oven.dish)
                    print("записали в список", time_list)
            print("Это временной список для готовности блюда", time_list)
            if time_list:
                for dish in time_list:
                    print("Записываем статус блюда на почти готово", dish)
                    dish_object = await self.get_dish_object(dish)
                    print("Это номер заказа", dish_object.one_dish_order)
                    if dish_object.one_dish_order:
                        print("заказ почти готов", dish.order_ref_id)
            await asyncio.sleep(1)

    async def time_changes_monitor(self):
        """Отслеживает наступление события изменения времени выпечки для информирования о готовности блюд
        """
        while True:
            await self.oven_time_changes_event["event"].wait()
            print("**:*:?*?*?*?*?%? СРАБОТАЛ event")
            print("Результат", self.oven_time_changes_event["result"])
            await self.stop_baking_time_setter()
            lock = asyncio.Lock()
            async with lock:
                self.oven_time_changes_event["event"].clear()
                self.oven_time_changes_event["result"] = None

    async def stop_baking_time_setter(self):
        futura_result = await self.oven_time_changes_event["result"]
        print(futura_result)
        for oven in futura_result:
            print(oven)
            self.equipment.ovens.oven_units[oven].stop_baking_time = futura_result[oven]
            print("Это результат сетера", self.equipment.ovens.oven_units[oven].stop_baking_time)

    async def broken_equipment_handler(self, event_params, equipment):
        """Этот метод обрабатывает поломки оборудования, поступающий на event_listener
        :param event_params: dict вида {unit_type: str, unit_id: uuid}
        """
        print("Обрабатываем уведомление об поломке оборудования", time.time())
        BROKEN_STATUS = "broken"
        unit_type = event_params["unit_type"]
        unit_id = event_params["unit_name"]
        try:
            if unit_type != "ovens":
                print("Меняем данные оборудования")
                getattr(equipment, unit_type)[unit_id] = False
            else:
                print("Меняем данные печи")
                await self.broken_oven_handler(unit_id)
        except KeyError:
            print("Ошибка данных оборудования")

    async def get_dish_status(self, dish_id):
        """Этот метод получает статус блюда  по заданному ID"""
        for order in self.current_orders_proceed:
            for dish in order:
                if dish.id == dish_id:
                    return dish.status

    async def get_dish_object(self, dish_id):
        """Этот метод возращает экземпляр класса блюда по заданному ID"""
        for order in self.current_orders_proceed.values():
            for dish in order.dishes:
                if dish.id == dish_id:
                    return dish

    async def change_oven_in_dish(self, dish_object, new_oven_object):
        """ Этот метод переназнаает печь в блюде
        :param dish_object: объект блюда
        :param new_oven_object: объект печи
        :return: dish instance BaseDish class
        """
        dish_object.oven_unit = new_oven_object

    async def broken_oven_handler(self, broken_oven_id):
        """ Этот метод обрабатывает поломку печи"""
        print("Обрабатываем уведомление о поломке печи", broken_oven_id)
        BROKEN_STATUS = "broken"
        ovens_list = self.equipment.ovens.oven_units
        oven_status = ovens_list[broken_oven_id].status
        print("СТАТУС сломанной ПЕЧИ", oven_status)
        if oven_status != "free":
            dish_id_in_broken_oven = ovens_list[broken_oven_id].dish
            new_oven_object = await self.equipment.ovens.oven_reserve(dish_id_in_broken_oven)
            dish_object = await self.get_dish_object(dish_id_in_broken_oven)
            if oven_status == "reserved":
                try:
                    print("Печь забронирована, нужно переназначить печь")
                    ovens_list[broken_oven_id].dish = None
                    await self.change_oven_in_dish(dish_object, new_oven_object)
                except OvenReservationError:
                    pass
            elif oven_status == "occupied":
                print("Печь занята, блюдо готовится")
                dish_status = await self.get_dish_status(dish_id_in_broken_oven)
                await self.change_oven_in_dish(dish_object, new_oven_object)
                if dish_status == "cooking":
                    print("Запутить смену лопаток в высокий приоритет")
                    await self.high_priority_queue.put((Recipy.switch_vane_cut_oven, (new_oven_object.oven_id,
                                                                                      broken_oven_id)))
                    ovens_list[broken_oven_id].dish = None
                elif dish_status == "baking":
                    print("Запустить ликвидацю блюда")
                    await self.low_priority_queue.put(dish_object.throwing_away_chain_list)
            elif oven_status == "waiting_15" or "waiting_60":
                # не сделано
                pass
        self.equipment.ovens.oven_units[broken_oven_id].status = BROKEN_STATUS
        print("Мы обработали печь")

    async def qr_code_handler(self, params):
        """Этот метод проверяет, есть ли заказ с таким чек кодом в current_orders_proceed.
        Входные данные params: полученный от контроллера словарь с чек кодом заказа и окном выдачи
        "ref_id": int, "pickup": int"""
        try:
            order_check_code = params["ref_id"]
            pickup_point = params["pickup"]
        except KeyError:
            print("Ошибка ключа, что делать?")
        set_mode_param = await self.evaluation_status_to_set_mode(order_check_code)
        if set_mode_param == "ready":
            self.orders_requested_for_delivery[order_check_code] = order_check_code
            asyncio.create_task(self.delivery_request_handler(order_check_code))
            self.current_orders_proceed[order_check_code].pickup_point = pickup_point
        await Controllers.set_pickup_point_mode(set_mode_param, pickup_point)
        # не доделано
        # await self.high_priority_queue.put(qr_code_data)

    async def evaluation_status_to_set_mode(self, order_check_code):
        """Передает контроллу значение, на основании которого пользователю
        выводится информация о заказе на экране пункта выдачи
        """
        CNTRLS_SET_MODE_OPTIONS = {1: "not_found",
                                   2: "in_progress",
                                   3: "ready"}
        OPTIONS = {
            "received": 2,
            "cooking": 2,
            "ready": 3,
            "informed": 3,
            "failed_to_be_cooked": 3
        }
        if order_check_code in self.current_orders_proceed:
            order_status = self.current_orders_proceed[order_check_code].status
            try:
                set_mode = CNTRLS_SET_MODE_OPTIONS[OPTIONS[order_status]]
            except KeyError:
                print("статус блюда не распознан")
                set_mode = "not_found"
        else:
            set_mode = "not_foun*d"
        return set_mode

    async def delivery_request_handler(self, order_check_code):
        """Запускает процедуру выдачи заказа
        ДОБАВИТЬ ОЧИСТКУ поля ПЕЧЬ после упаковке --> oven_unit = None"""
        for dish in self.current_orders_proceed[order_check_code].dishes:
            print("Вот это блюдо выдаем", dish)
            # не сделано

    def __repr__(self):
        return f"{COOKINGMODE}"
