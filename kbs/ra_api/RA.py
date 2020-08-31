"""Это служебный модуль, имитирующий API робота-манипулятора
Написан для тестов работоспособности по-черному :) """


import asyncio
import random
import time


class RAError(Exception):
    """Класс ошибок ra_api"""
    pass


# это просто эмуляция работы ra_api, необходимая для тестирования PBM
class Movement(object):
    """Эмуляция работы ra_api для нужд PBM"""

    @staticmethod
    async def movement(n):
        # print("__ ra_api начал работу")
        await asyncio.sleep(n)
        result = random.choice([True, True])
        # print("__ Работа ra_api завершена")
        return result


class RA(Movement):

    @classmethod
    async def get_position_move_time(clx, from_place: str, to_place: str):
        """

        метод рассчитывает время на перемещение между точками.
        Эмуляция работы: возвращает случайным образом список
        из вариантов или пустой если точка не найдена.

        UPD возвращает мин время
        :param
           from_place: str
           to_place: srt
        :return: possible_duration (list[int])
        """
        result_choice = random.choice([(5, 6, 8, 9, 7)])
        return result_choice

    @classmethod
    async def position_move(cls, place: str, duration: float):
        """
        :param place: str
        :param duration: float
        :return: int if succeed
                 raiseError if not
                 # нужно определить типы ошибок
        """
        print(f"RA-API {time.time()} двигается к {place} за {duration} сек")
        result = await cls.movement(duration)
        print(f"RA-API {time.time()} доехал к {place} за {duration} сек")
        print()
        if result:
            return duration
        else:
            raise RAError

    @classmethod
    async def get_atomic_action_time(clx, **kwargs):
        """
        :param name: имя пакета атомарных действий, str
        :param place: id оборудования
        :return: int если успешно
        :raise RAError
        """
        # return random.randint(1, 10)
        return 5

    @classmethod
    async def start_atomic_action(cls, **kwargs):
        place = kwargs["place"]
        atomic_name = kwargs["name"]
        print(f"RA-API {time.time()} выполняет атомарное действие {atomic_name}")
        result = await cls.movement(5)
        print(f"RA-API {time.time()} stop атомарное действие {atomic_name}")
        print()
        return result

    @classmethod
    async def dance(cls):
        print(f"RA-API {time.time()} Танцуем")
        print()
        await asyncio.sleep(1)

    @classmethod
    async def dance_for_time(cls, duration):
        print(f"RA-API {time.time()} Танцуем экстра")
        print()
        await asyncio.sleep(duration)
        return True

    @classmethod
    async def get_current_position(cls):
        """Возвращает текущее местоположение ra_api"""
        return "oven 1"

    @classmethod
    async def get_current_gripper(cls):
        # gripper_options = ["product", None]
        gripper_options = [None]
        return random.choice(gripper_options)

    async def start_on(self):
        """включение"""
        pass

    async def shout_down(self):
        """выключение"""
        pass

