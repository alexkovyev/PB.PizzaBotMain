"""Этот модуль содержит методы, используемые
при создании нового заказа """

from ..order import Order
from kbs.exceptions import OvenReserveFailed, OvenReservationError


class OrderInitialData(object):
    """Этот класс объедняет методы для создания
    нового заказа
    """

    @staticmethod
    async def get_order_structure_from_db(new_order_check_code):
        """Этот метод вызывает процедуру 'Получи состав блюд в заказе' и возвращает словарь вида
        {"check_code": new_order_check_code,
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
        new_order = dict(check_code=new_order_check_code, dishes={"40576654-9f31-11ea-bb37-0242ac130002":
            {
                "dough": {"id": 2},
                "sauce": {"id": 2, "content": ((1, 5), (2, 25))},
                "filling": {"id": 1, "content": (
                    "tomato", "cheese", "ham", "olive", "pepper", "bacon")},
                "additive": {"id": 7}
            },
            "6327ade2-9f31-11ea-bb37-0242ac130002":
                {
                    "dough": {"id": 1},
                    "sauce": {"id": 2, "content": ((1, 5), (2, 25))},
                    "filling": {"id": 1, "content": (
                        "tomato", "cheese", "ham", "olive", "pepper",
                        "bacon")},
                    "additive": {"id": 1}
                }
        })
        return new_order

    @staticmethod
    async def create_sauce_recipe(recipe_base, dish):
        """

        :param recipe_base:
        :param dish:
        """
        sauce_id = dish["sauce"]["id"]
        dish["sauce"]["recipe"] = recipe_base["sauce"][sauce_id]
        for component, my_tuple in zip(dish["sauce"]["recipe"]["content"], dish["sauce"]["content"]):
            dish["sauce"]["recipe"]["content"][component]["qt"] = my_tuple[1]

    @staticmethod
    async def create_filling_recipe(recipe_base, dish):
        """Этот метод выбирает рецепт начинки для начинки в общем
        и для каждого компонента начинки в целом"""
        filling_id = dish["filling"]["id"]
        dough_id = dish["dough"]["id"]
        dish["filling"]["cooking_program"] = recipe_base["filling"][filling_id]["cooking_program"][dough_id]
        dish["filling"]["make_crust_program"] = recipe_base["filling"][filling_id]["make_crust_program"][dough_id]
        dish["filling"]["pre_heating_program"] = recipe_base["filling"][filling_id]["pre_heating_program"][
            dough_id]
        dish["filling"]["stand_by"] = recipe_base["filling"][filling_id]["stand_by_program"][dough_id]
        halfstaff_content = dish["filling"]["content"]
        cutting_program = recipe_base["filling"][filling_id]["cutting_program"]
        dish["filling"]["content"] = [list(_) for _ in (zip(halfstaff_content, cutting_program))]
        print("Составили рецепт начинки", dish["filling"])

    @classmethod
    async def join_recipe_data(cls, recipe_dict, new_order):
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

        # print("Входные данные", new_order_check_code)

        for dish in new_order.values():
            dish["dough"]["recipe"] = recipe_dict["dough"]
            await cls.create_sauce_recipe(recipe_dict, dish)
            await cls.create_filling_recipe(recipe_dict, dish)
            dish["additive"]["recipe"] = recipe_dict["additive"]

    @staticmethod
    async def reserve_oven(new_order, equipment_data):
        """ Этот метод резервирует печи для каждого блюда в заказе
        :param equipment_data:
        :param new_order: str
        :return list of OvenUnit instance selected for the order
        """
        try:
            ovens_reserved = [await equipment_data.ovens.oven_reserve(dish) for dish in new_order["dishes"]]
            return ovens_reserved
        except OvenReservationError:
            raise OvenReserveFailed("Ошибка назначения печей на заказ. Нет свободных печей")

    @classmethod
    async def data_preperation_for_new_order(cls, new_order_check_code, recipe_data):
        """ Этот метод получает данные о составе заказа и получает данные, необходимые для
        приготовления этого заказа

        :param new_order_check_code: str uuid4
        :param recipe_data:
        :return: dict вида {"order_check_code": str,
                            "dishes": {"dish_id": {}
                                      }
                            }
        """
        order_content = await cls.get_order_structure_from_db(new_order_check_code)
        await cls.join_recipe_data(recipe_data, order_content["dishes"])
        return order_content
