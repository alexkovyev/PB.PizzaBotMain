class Utils(object):

    @staticmethod
    async def get_dish_object(dish_id, current_orders_proceed_dict):
        """Этот метод возращает экземпляр класса блюда по заданному ID"""

        for order in current_orders_proceed_dict.values():
            for dish in order.dishes:
                if dish.id == dish_id:
                    return dish

    @staticmethod
    async def change_oven_in_dish(dish_object, new_oven_object):
        """ Этот метод переназнаает печь в блюде
        :param dish_object: объект блюда
        :param new_oven_object: объект печи
        :return: dish instance BaseDish class
        """
        dish_object.oven_unit = new_oven_object

    @staticmethod
    async def put_chains_in_queue(dish, queue):
        """Добавляет чейны рецепта в очередь в виде кортежа (dish, chain)"""
        chains = dish.cooking_recipe
        for chain in chains:
            await queue.put(chain)