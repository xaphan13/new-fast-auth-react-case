Изучив код в `my_stream_map.py`, я создам класс для работы с потоками в стиле Java Stream API. Вот реализация:Я создал класс `MyStream`, который реализует функциональность в стиле Java Stream API для Python. Основные особенности:

## Ключевые функции:

**Промежуточные операции (возвращают новый поток):**

-   `map()` - преобразование элементов
-   `filter()` - фильтрация по предикату
-   `flat_map()` - преобразование и разворачивание в плоский поток
-   `distinct()` - удаление дубликатов
-   `limit()` - ограничение количества элементов
-   `skip()` - пропуск элементов
-   `sorted()` - сортировка

**Терминальные операции (завершают поток):**

-   `to_list()`, `to_set()` - сбор в коллекции
-   `count()` - подсчет элементов
-   `for_each()` - выполнение действия для каждого элемента
-   `reduce()` - редукция (свертка)
-   `find_first()` - получение первого элемента
-   `any_match()`, `all_match()`, `none_match()` - проверки

## Преимущества над оригинальным кодом:

1.  **Ленивые вычисления** - операции выполняются только при вызове терминальной операции
2.  **Цепочки операций** - можно строить сложные пайплайны обработки данных
3.  **Типизация** - поддержка generic типов для безопасности типов
4.  **Полный API** - реализованы все основные операции из Java Stream
5.  **Гибкость** - можно создавать потоки из любых итерируемых объектов

## Пример использования из оригинального кода:

```python
# Ваш оригинальный пример:
numbers = [2, 3, 4, 5, 6]
result = (
    MyStream.from_iterable(numbers)
    .map(lambda x: x**2)
    .flat_map(lambda x: (x, x + 1))
    .filter(lambda x: x <= 36)
    .map(str)
    .to_list()
)
```

Класс предоставляет более удобный и функциональный способ работы с данными в стиле потокового программирования!


```python
import itertools
from typing import Iterable, Callable, TypeVar, Generic, List, Any, Optional

T = TypeVar("T")
R = TypeVar("R")


class MyStream(Generic[T]):
    """
    Класс для работы с потоками данных в стиле Java Stream API.
    Поддерживает ленивые вычисления и цепочки операций.
    """

    def __init__(self, data: Iterable[T]):
        """
        Инициализация потока данными.

        Args:
            data: Итерируемый объект с данными
        """
        self._data = data

    @classmethod
    def of(cls, *elements: T) -> "MyStream[T]":
        """
        Создает поток из переданных элементов.

        Args:
            *elements: Элементы для создания потока

        Returns:
            MyStream: Новый поток с элементами
        """
        return cls(elements)

    @classmethod
    def from_iterable(cls, iterable: Iterable[T]) -> "MyStream[T]":
        """
        Создает поток из итерируемого объекта.

        Args:
            iterable: Итерируемый объект

        Returns:
            MyStream: Новый поток
        """
        return cls(iterable)

    def map(self, mapper: Callable[[T], R]) -> "MyStream[R]":
        """
        Применяет функцию к каждому элементу потока.

        Args:
            mapper: Функция для преобразования элементов

        Returns:
            MyStream: Новый поток с преобразованными элементами
        """
        return MyStream(map(mapper, self._data))

    def filter(self, predicate: Callable[[T], bool]) -> "MyStream[T]":
        """
        Фильтрует элементы потока по предикату.

        Args:
            predicate: Функция-предикат для фильтрации

        Returns:
            MyStream: Новый поток с отфильтрованными элементами
        """
        return MyStream(filter(predicate, self._data))

    def flat_map(self, mapper: Callable[[T], Iterable[R]]) -> "MyStream[R]":
        """
        Применяет функцию к каждому элементу и "разворачивает" результаты в один поток.

        Args:
            mapper: Функция, возвращающая итерируемый объект

        Returns:
            MyStream: Новый поток с развернутыми элементами
        """
        mapped_data = map(mapper, self._data)
        flattened_data = itertools.chain.from_iterable(mapped_data)
        return MyStream(flattened_data)

    def distinct(self) -> "MyStream[T]":
        """
        Удаляет дублирующиеся элементы из потока (сохраняет порядок первого вхождения).

        Returns:
            MyStream: Новый поток без дубликатов
        """

        def unique_generator():
            seen = set()
            for item in self._data:
                if item not in seen:
                    seen.add(item)
                    yield item

        return MyStream(unique_generator())

    def limit(self, max_size: int) -> "MyStream[T]":
        """
        Ограничивает количество элементов в потоке.

        Args:
            max_size: Максимальное количество элементов

        Returns:
            MyStream: Новый поток с ограниченным количеством элементов
        """
        return MyStream(itertools.islice(self._data, max_size))

    def skip(self, n: int) -> "MyStream[T]":
        """
        Пропускает первые n элементов потока.

        Args:
            n: Количество элементов для пропуска

        Returns:
            MyStream: Новый поток без первых n элементов
        """
        return MyStream(itertools.islice(self._data, n, None))

    def sorted(
        self, key: Optional[Callable[[T], Any]] = None, reverse: bool = False
    ) -> "MyStream[T]":
        """
        Сортирует элементы потока.

        Args:
            key: Функция для извлечения ключа сортировки
            reverse: Сортировать в обратном порядке

        Returns:
            MyStream: Новый поток с отсортированными элементами
        """
        return MyStream(sorted(self._data, key=key, reverse=reverse))

    # Терминальные операции (завершающие)

    def to_list(self) -> List[T]:
        """
        Собирает все элементы потока в список.

        Returns:
            List: Список всех элементов потока
        """
        return list(self._data)

    def to_set(self) -> set:
        """
        Собирает все элементы потока в множество.

        Returns:
            set: Множество всех элементов потока
        """
        return set(self._data)

    def count(self) -> int:
        """
        Возвращает количество элементов в потоке.

        Returns:
            int: Количество элементов
        """
        return sum(1 for _ in self._data)

    def for_each(self, action: Callable[[T], None]) -> None:
        """
        Применяет действие к каждому элементу потока.

        Args:
            action: Действие для применения к каждому элементу
        """
        for item in self._data:
            action(item)

    def reduce(self, accumulator: Callable[[R, T], R], identity: R) -> R:
        """
        Выполняет редукцию элементов потока.

        Args:
            accumulator: Функция аккумуляции
            identity: Начальное значение

        Returns:
            R: Результат редукции
        """
        result = identity
        for item in self._data:
            result = accumulator(result, item)
        return result

    def find_first(self) -> Optional[T]:
        """
        Возвращает первый элемент потока.

        Returns:
            Optional[T]: Первый элемент или None, если поток пуст
        """
        try:
            return next(iter(self._data))
        except StopIteration:
            return None

    def any_match(self, predicate: Callable[[T], bool]) -> bool:
        """
        Проверяет, есть ли хотя бы один элемент, удовлетворяющий предикату.

        Args:
            predicate: Функция-предикат

        Returns:
            bool: True, если есть хотя бы один подходящий элемент
        """
        return any(predicate(item) for item in self._data)

    def all_match(self, predicate: Callable[[T], bool]) -> bool:
        """
        Проверяет, все ли элементы удовлетворяют предикату.

        Args:
            predicate: Функция-предикат

        Returns:
            bool: True, если все элементы удовлетворяют предикату
        """
        return all(predicate(item) for item in self._data)

    def none_match(self, predicate: Callable[[T], bool]) -> bool:
        """
        Проверяет, что ни один элемент не удовлетворяет предикату.

        Args:
            predicate: Функция-предикат

        Returns:
            bool: True, если ни один элемент не удовлетворяет предикату
        """
        return not self.any_match(predicate)


# Демонстрационные функции
def demo_basic_operations():
    """Демонстрация базовых операций"""
    print("=== Базовые операции ===")

    # Пример из оригинального кода, адаптированный под MyStream
    numbers = [2, 3, 4, 5, 6]

    result = (
        MyStream.from_iterable(numbers)
        .map(lambda x: x**2)  # возводим в квадрат
        .flat_map(lambda x: (x, x + 1))  # из каждого элемента получаем пару
        .filter(lambda x: x <= 36)  # фильтруем
        .map(str)  # преобразуем в строку
        .to_list()
    )

    print(f"Результат цепочки операций: {result}")


def demo_advanced_operations():
    """Демонстрация продвинутых операций"""
    print("\n=== Продвинутые операции ===")

    # Работа со строками
    words = ["apple", "banana", "cherry", "date", "elderberry"]

    # Найти все уникальные символы из слов длиннее 5 символов
    unique_chars = (
        MyStream.from_iterable(words)
        .filter(lambda word: len(word) > 5)
        .flat_map(lambda word: word)  # разбиваем слово на символы
        .distinct()
        .sorted()
        .to_list()
    )

    print(f"Уникальные символы из длинных слов: {unique_chars}")

    # Статистика по числам
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    sum_of_squares = (
        MyStream.from_iterable(numbers)
        .filter(lambda x: x % 2 == 0)  # только четные
        .map(lambda x: x**2)  # в квадрат
        .reduce(lambda acc, x: acc + x, 0)
    )  # сумма

    print(f"Сумма квадратов четных чисел: {sum_of_squares}")

    # Проверки
    has_big_numbers = MyStream.from_iterable(numbers).any_match(lambda x: x > 8)

    all_positive = MyStream.from_iterable(numbers).all_match(lambda x: x > 0)

    print(f"Есть числа больше 8: {has_big_numbers}")
    print(f"Все числа положительные: {all_positive}")


def demo_complex_example():
    """Сложный пример с обработкой данных"""
    print("\n=== Сложный пример ===")

    # Имитируем данные о товарах
    products = [
        {"name": "Laptop", "category": "Electronics", "price": 999, "tags": ["computer", "work"]},
        {"name": "Mouse", "category": "Electronics", "price": 25, "tags": ["computer", "gaming"]},
        {"name": "Book", "category": "Education", "price": 15, "tags": ["learning", "reading"]},
        {"name": "Keyboard", "category": "Electronics", "price": 75, "tags": ["computer", "work"]},
        {"name": "Notebook", "category": "Education", "price": 5, "tags": ["writing", "learning"]},
    ]

    # Найдем все теги товаров из категории Electronics дороже 50, отсортированные по алфавиту
    electronics_tags = (
        MyStream.from_iterable(products)
        .filter(lambda p: p["category"] == "Electronics")
        .filter(lambda p: p["price"] > 50)
        .flat_map(lambda p: p["tags"])
        .distinct()
        .sorted()
        .to_list()
    )

    print(f"Теги дорогой электроники: {electronics_tags}")

    # Средняя цена товаров по категориям
    categories = MyStream.from_iterable(products).map(lambda p: p["category"]).distinct().to_list()

    for category in categories:
        avg_price = (
            MyStream.from_iterable(products)
            .filter(lambda p: p["category"] == category)
            .map(lambda p: p["price"])
            .reduce(lambda acc, price: acc + price, 0)
        ) / (MyStream.from_iterable(products).filter(lambda p: p["category"] == category).count())

        print(f"Средняя цена в категории {category}: ${avg_price:.2f}")


if __name__ == "__main__":
    demo_basic_operations()
    demo_advanced_operations()
    demo_complex_example()
```
# ------------------------------
