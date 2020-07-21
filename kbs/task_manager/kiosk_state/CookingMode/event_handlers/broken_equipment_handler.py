class BrokenOvenHandler(object):

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

