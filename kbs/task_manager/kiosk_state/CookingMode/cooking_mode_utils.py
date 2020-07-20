class Utils(object):

    @staticmethod
    async def get_dish_object(dish_id, current_orders_proceed_dict):
        """Этот метод возращает экземпляр класса блюда по заданному ID"""

        for order in current_orders_proceed_dict.values():
            for dish in order.dishes:
                if dish.id == dish_id:
                    return dish

    @staticmethod
    async def get_dish_status(dish_id, current_orders_proceed_dict):
        """Этот метод получает статус блюда  по заданному ID"""
        for order in current_orders_proceed_dict:
            for dish in order:
                if dish.id == dish_id:
                    return dish.status
