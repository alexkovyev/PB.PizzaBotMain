import asyncio
import random
import time


class RAError(Exception):
    """Класс ошибок RA"""

    def __init__(self):
        self.text = "Возникла ошибка RA"


# это просто эмуляция работы RA, необходимая для тестирования PBM
class Movement(object):
    """Эмуляция работы RA для нужд PBM"""

    @staticmethod
    async def movement(n):
        print("__ RA начал работу")
        await asyncio.sleep(n)
        result = random.choice([True, True])
        print("__ Работа RA завершена")
        return result


class RA(Movement):

    @classmethod
    async def get_position_move_time(clx, from_place: str, to_place: str):
        """ метод рассчитывает время на перемещение между точками.
        Эмуляция работы: возвращает случайным образом список
        из вариантов или пустой если точка не найдена.
        :param
           from_place: str
           to_place: srt
        :return: possible_duration (list[int])
        """
        result_choice = random.choice([[5, 6, 3, 2, 1], [4, 5, 6, 3, 1], [4, 5, 6, 3, 1]])
        return result_choice

    @classmethod
    async def position_move(cls, place: str, duration: int):
        """
        :param place: str
        :param duration: int
        :return: int if succeed
                 raiseError if not
                 # нужно определить типы ошибок
        """
        print(f"RA двигается к {place} за {duration} сек", time.time())
        result = await cls.movement(duration)
        print("RA доехал", time.time())
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
        print("Атомарное действие", kwargs["name"])
        return random.randint(1,10)

    @classmethod
    async def atomic_action(cls, **kwargs):
        place = kwargs["place"]
        atomic_name = kwargs["name"]
        print("RA выполняет атомарное действие", atomic_name)
        duration = random.randint(1, 10)
        result = await cls.movement(duration)
        return result

    @classmethod
    async def dance(cls):
        print("Танцуем", time.time())
        await asyncio.sleep(1)

    @classmethod
    async def dance_for_time(cls, duration):
        print("Танцуем экстра", time.time())
        await asyncio.sleep(duration)
        return True

    @classmethod
    async def get_current_position(cls):
        """Возвращает текущее местоположение RA"""
        return "oven 1"

    @classmethod
    async def get_current_gripper(cls):
        gripper_options = ["product", None]
        return random.choice(gripper_options)

