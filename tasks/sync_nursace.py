import csv
import logging
import aiofiles
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from nursace_models import (
    Product, Category, Manufacturer, Collection, Season, Sex, Color, Material,
    MeasureUnit, Currency, ProductCurrencyPrice, Analog
)
from config.nursace_database import async_session_maker

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Категории верхнего уровня, которые нужно полностью исключить из загрузки
EXCLUDED_ROOT_CATEGORIES = {"Одежда"}

# Утилиты для нормализации заголовков CSV

def normalize_header_key(key: str) -> str:
    if key is None:
        return key
    return key.strip().lstrip("\ufeff")

def normalize_field_name(name: str) -> str:
    if name is None:
        return name
    name = normalize_header_key(name)
    # Нижний регистр и удаление не буквенно-цифровых символов
    return "".join(ch for ch in name.lower() if ch.isalnum())

def make_row_index(row: dict) -> dict:
    # Создаёт индекс по нормализованным именам столбцов
    indexed = {}
    for k, v in row.items():
        indexed[normalize_field_name(k)] = v
    return indexed

def row_get(indexed_row: dict, *names: str):
    # Ищет значение по нескольким вариантам имён столбцов
    for name in names:
        val = indexed_row.get(normalize_field_name(name))
        if val is not None:
            return val
    return None

def parse_int(value: str) -> int | None:
    if not value or not str(value).strip():
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        logger.warning(f"Не удалось преобразовать в int: {value}")
        return None
    
def parse_float(value: str) -> float | None:
    if not value or not str(value).strip():
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        logger.warning(f"Не удалось преобразовать в float: {value}")
        return None

async def sync_torgsoft_csv_nursace() -> dict:
    """
    Синхронизирует данные из CSV-файла Торгсофт (torgsoft/TSGoods.csv) с базой данных.

    Returns:
        dict: Статистика синхронизации (количество созданных/обновленных записей).
    """
    stats = {
        "products_created": 0,
        "products_updated": 0,
        "categories_created": 0,
        "manufacturers_created": 0,
        "collections_created": 0,
        "seasons_created": 0,
        "sexes_created": 0,
        # "colors_created": 0,
        "materials_created": 0,
        "measure_units_created": 0,
        "currencies_created": 0,
        "attributes_created": 0,
        "currency_prices_created": 0,
        "analogs_created": 0,
        "skipped_products": 0,
        "rows_without_goodid": 0,
    }

    async def get_or_create(model, filter_field, filter_value, defaults=None, session=None):
        """Получает или создает запись в таблице, избегая дубликатов."""
        try:
            query = select(model).where(getattr(model, filter_field) == filter_value)
            result = await session.execute(query)
            instance = result.scalars().first()
            if instance:
                return instance, False
            instance = model(**{filter_field: filter_value, **(defaults or {})})
            session.add(instance)
            return instance, True
        except SQLAlchemyError as e:
            logger.error(f"Ошибка в get_or_create для {model.__name__}, поле {filter_field}: {str(e)}")
            # Откатываем транзакцию и создаем новую сессию
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка в get_or_create для {model.__name__}, поле {filter_field}: {str(e)}")
            await session.rollback()
            raise

    async def get_or_create_hierarchy(model, parent_field, name_field, names, parent_id=None, defaults=None, session=None):
        """Обрабатывает иерархию (например, для категорий или коллекций)."""
        try:
            current_parent_id = parent_id
            last_instance = None
            for name in names:
                instance, created = await get_or_create(
                    model,
                    name_field,
                    name,
                    defaults={parent_field: current_parent_id, **(defaults or {})},
                    session=session
                )
                if created:
                    stats[f"{model.__tablename__}_created"] += 1
                last_instance = instance
                # Явно указываем правильное имя идентификатора
                id_field = 'category_id' if model.__name__ == 'Category' else 'collection_id' if model.__name__ == 'Collection' else 'id'
                current_parent_id = getattr(instance, id_field)
            return last_instance
        except SQLAlchemyError as e:
            logger.error(f"Ошибка в get_or_create_hierarchy для {model.__name__}: {str(e)}")
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка в get_or_create_hierarchy для {model.__name__}: {str(e)}")
            await session.rollback()
            raise

    # Чтение CSV-файла
    try:
        logger.info("Старт синхронизации: torgsoft/TSGoods.csv")
        # async with aiofiles.open("shared_files/TSGoods.csv", mode="r", encoding="utf-8") as csv_file:
        async with aiofiles.open("torgsoft/TSGoods.csv", mode="r", encoding="utf-8") as csv_file:
            content = await csv_file.read()

            # Определяем разделитель автоматически (поддержка "," и ";")
            lines = content.splitlines()
            sample = "\n".join(lines[:5])
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;")
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ","
            logger.info(f"Определён разделитель CSV: '{delimiter}', всего строк: {len(lines)}")
            reader = csv.DictReader(lines, delimiter=delimiter)

            # Детекторы/флаги
            logged_headers_once = False
            detected_good_id_key = None  # нормализованное имя ключа GoodID, если найдено эвристикой
            processed_rows = 0
            commit_batch_size = 100  # Размер батча для коммита

            for row in reader:
                processed_rows += 1
                if processed_rows % 1000 == 0:
                    logger.info(f"Прогресс: обработано {processed_rows} строк")

                # Создаем новую сессию для каждой строки или батча
                if processed_rows % commit_batch_size == 1:
                    # Закрываем предыдущую сессию если она существует
                    if 'session' in locals():
                        try:
                            await session.close()
                        except:
                            pass
                    
                    # Создаем новую сессию
                    session = async_session_maker()
                    try:
                        await session.begin()
                    except Exception as e:
                        logger.error(f"Ошибка при создании сессии: {str(e)}")
                        continue

                try:
                    # Нормализуем ключи заголовков (убираем BOM/пробелы) и строим индекс
                    row = {normalize_header_key(k): v for k, v in row.items()}
                    row_idx = make_row_index(row)

                    # Однократно логируем заголовки для диагностики
                    if not logged_headers_once:
                        logger.info(f"CSV headers: {list(row.keys())}")
                        logged_headers_once = True

                    # Извлекаем значения с учётом возможных вариантов имён столбцов
                    goodtypefull_value = row_get(row_idx, "GoodTypeFull", "GoodType", "Good Type Full", "Good_Type_Full")

                    # Проверяем наличие GoodID (учёт разных вариантов имён)
                    good_id_raw = row_get(row_idx, "GoodID", "Good Id", "Good_Id", "ID", "Id")

                    # Если не нашли по алиасам — пробуем автоматически определить колонку GoodID
                    if (not good_id_raw or not str(good_id_raw).strip()):
                        if detected_good_id_key and row_idx.get(detected_good_id_key) is not None:
                            good_id_raw = row_idx.get(detected_good_id_key)
                        else:
                            # Эвристика: ищем ключ, содержащий 'good' и оканчивающийся на 'id', либо просто 'id'
                            candidate_keys = []
                            for k_norm, v in row_idx.items():
                                if v is None or not str(v).strip():
                                    continue
                                if ("good" in k_norm and k_norm.endswith("id")) or k_norm == "id" or k_norm.endswith("id"):
                                    if parse_int(v) is not None:
                                        candidate_keys.append(k_norm)
                            if candidate_keys:
                                detected_good_id_key = candidate_keys[0]
                                good_id_raw = row_idx.get(detected_good_id_key)
                                logger.info(f"Detected GoodID column: {detected_good_id_key}")

                    # Теперь парсим good_id
                    if not good_id_raw or not str(good_id_raw).strip():
                        stats["rows_without_goodid"] += 1
                        logger.debug(f"Пропуск строки без GoodID (row {processed_rows})")
                        continue
                    good_id = parse_int(good_id_raw)
                    if good_id is None:
                        stats["rows_without_goodid"] += 1
                        logger.debug(f"Пропуск строки с некорректным GoodID (row {processed_rows})")
                        continue

                    # Пропуск строк по верхнему уровню GoodTypeFull (например, Одежда)
                    first_category_name = None
                    if goodtypefull_value:
                        first_category_name = str(goodtypefull_value).split(",")[0].strip()
                        if first_category_name in EXCLUDED_ROOT_CATEGORIES:
                            stats["skipped_products"] += 1
                            logger.info(f"SKIP: GoodID={good_id} из-за категории: {first_category_name}")
                            continue

                    logger.debug(f"ROW: {processed_rows} GoodID={good_id} root_category={first_category_name}")

                    # Обработка справочных данных
                    # Категории (GoodTypeFull)
                    category_id = None
                    if goodtypefull_value:
                        category_names = [name.strip() for name in str(goodtypefull_value).split(",") if name.strip()]
                        try:
                            category = await get_or_create_hierarchy(
                                Category, "parent_category_id", "category_name", category_names,
                                defaults={"synchronization_section": category_names[0] if category_names else None},
                                session=session
                            )
                            category_id = category.category_id if category else None
                            logger.debug(f"Категория обработана: {category_names}, category_id={category_id}")
                        except Exception as e:
                            logger.error(f"Ошибка при обработке категорий {category_names}: {str(e)}")
                            continue  # Пропускаем товар, если ошибка в категориях

                    # Производитель и страна
                    country_name = row_get(row_idx, "Country", "Страна") or "Unknown"
                    manufacturer, created = await get_or_create(
                        Manufacturer, "manufacturer_name", country_name,
                        defaults={"country": country_name},
                        session=session
                    )
                    if created:
                        stats["manufacturers_created"] += 1
                        logger.debug(f"Создан производитель: {country_name}")

                    # Коллекции (ProducerCollectionFull)
                    producer_collection_full = row_get(row_idx, "ProducerCollectionFull", "ProducerCollection", "Producer Collection Full")
                    if producer_collection_full:
                        collection_names = [name.strip() for name in str(producer_collection_full).split(",") if name.strip()]
                        collection = await get_or_create_hierarchy(
                            Collection, "parent_collection_id", "collection_name", collection_names,
                            defaults={"manufacturer_id": manufacturer.manufacturer_id},
                            session=session
                        )
                        collection_id = collection.collection_id if collection else None
                    else:
                        collection_id = None

                    # Сезон
                    season_name = row_get(row_idx, "Season", "Сезон") or "Unknown"
                    season, created = await get_or_create(Season, "season_name", season_name, session=session)
                    if created:
                        stats["seasons_created"] += 1
                        logger.debug(f"Создан сезон: {season_name}")

                    # Пол
                    sex_value = parse_int(row_get(row_idx, "Sex", "Пол")) or 0
                    sex_mapping = {
                        0: "Не определен",
                        1: "Мужской",
                        2: "Женский",
                        3: "Мальчик",
                        4: "Девочка",
                        5: "Унисекс"
                    }
                    sex_name = sex_mapping.get(sex_value, "Не определен")
                    sex, created = await get_or_create(Sex, "sex_name", sex_name, session=session)
                    if created:
                        stats["sexes_created"] += 1
                        logger.debug(f"Создан пол: {sex_name}")

                    # Материал
                    material_name = row_get(row_idx, "Material", "Материал") or "Unknown"
                    material, created = await get_or_create(Material, "material_name", material_name, session=session)
                    if created:
                        stats["materials_created"] += 1
                        logger.debug(f"Создан материал: {material_name}")

                    # Единица измерения
                    measure_unit_name = row_get(row_idx, "MeasureUnit", "Measure Unit", "ЕдИзм") or "Unknown"
                    measure_unit, created = await get_or_create(MeasureUnit, "unit_name", measure_unit_name, session=session)
                    if created:
                        stats["measure_units_created"] += 1
                        logger.debug(f"Создана единица измерения: {measure_unit_name}")

                    # Валюта (если есть EqualCurrencyName)
                    currency_name = row_get(row_idx, "EqualCurrencyName", "Currency", "Валюта") or None
                    currency_id = None
                    if currency_name:
                        currency, created = await get_or_create(Currency, "currency_name", currency_name, session=session)
                        if created:
                            stats["currencies_created"] += 1
                            logger.debug(f"Создана валюта: {currency_name}")
                        currency_id = currency.currency_id

                    # Товар
                    query = select(Product).where(Product.good_id == good_id)
                    result = await session.execute(query)
                    product = result.scalars().first()

                    # Базовые данные товара (без display и color_id)
                    product_data = {
                        "good_name": row_get(row_idx, "GoodName", "Name", "Наименование"),
                        "short_name": row_get(row_idx, "ShortName", "Short Name") or None,
                        "description": row_get(row_idx, "Description", "Опис", "Описание") or None,
                        "articul": row_get(row_idx, "Articul", "Артикул") or None,
                        "barcode": row_get(row_idx, "Barcode", "Штрихкод") or None,
                        "retail_price": parse_float(row_get(row_idx, "RetailPrice", "Retail Price")),
                        "wholesale_price": parse_float(row_get(row_idx, "WholesalePrice", "Wholesale Price")),
                        "retail_price_with_discount": parse_float(row_get(row_idx, "RetailPriceWithDiscount")),
                        "prime_cost": parse_float(row_get(row_idx, "PrimeCost", "Себестоимость")),
                        "equal_sale_price": parse_float(row_get(row_idx, "EqualSalePrice")),
                        "equal_wholesale_price": parse_float(row_get(row_idx, "EqualWholesalePrice")),
                        "price_discount_percent": parse_float(row_get(row_idx, "PriceDiscountPercent")),
                        "min_quantity_for_order": parse_int(row_get(row_idx, "MinQuantityForOrder")),
                        "wholesale_count": parse_float(row_get(row_idx, "WholesaleCount")),
                        "warehouse_quantity": parse_float(row_get(row_idx, "WarehouseQuantity")),
                        "measure": parse_float(row_get(row_idx, "Measure")),
                        "height": parse_float(row_get(row_idx, "Height")),
                        "width": parse_float(row_get(row_idx, "Width")),
                        "closeout": parse_int(row_get(row_idx, "Closeout")),
                        "guarantee_period": parse_int(row_get(row_idx, "GuaranteePeriod", "Guarantee Period")) or None,
                        "category_id": category_id,
                        "manufacturer_id": manufacturer.manufacturer_id,
                        "collection_id": collection_id,
                        "season_id": season.season_id,
                        "sex_id": sex.sex_id,
                        # "color_id": color.color_id,  # Исключаем из обновления
                        "material_id": material.material_id,
                        "measure_unit_id": measure_unit.measure_unit_id,
                        "guarantee_mes_unit_id": measure_unit.measure_unit_id,
                        "supplier_code": row_get(row_idx, "SupplierCode") or None,
                        "model_good_id": parse_int(row_get(row_idx, "Category")) if row_get(row_idx, "Category") != "-1" else None,
                        "pack": row_get(row_idx, "Pack") or None,
                        "pack_size": row_get(row_idx, "PackSize", "Pack Size") or None,
                        "power_supply": row_get(row_idx, "PowerSupply", "Power Supply") or None,
                        "count_units_per_box": row_get(row_idx, "CountUnitsPerBox") or None,
                        "age": row_get(row_idx, "Age") or None,
                        "product_size": parse_float(row_get(row_idx, "TheSize", "Size")),
                        "fashion_name": row_get(row_idx, "FashionName") or None,
                        "retail_price_per_unit": parse_float(row_get(row_idx, "RetailPricePerUnit")),
                        "wholesale_price_per_unit": parse_float(row_get(row_idx, "WholesalePricePerUnit")),
                    }

                    if product:
                        logger.info(f"UPDATE: GoodID={good_id}")
                        # Для существующих товаров обновляем все поля кроме display и color_id
                        excluded_fields = {"display", "color_id"}
                        for key, value in product_data.items():
                            if key not in excluded_fields:
                                setattr(product, key, value)
                        stats["products_updated"] += 1
                    else:
                        logger.info(f"CREATE: GoodID={good_id}")
                        # Для новых товаров добавляем display = 1
                        product_data["display"] = 1
                        product = Product(good_id=good_id, **product_data)
                        session.add(product)
                        stats["products_created"] += 1

                    # Обработка аналогов
                    analogs_raw = row_get(row_idx, "Analogs")
                    if analogs_raw:
                        analog_ids = [int(aid) for aid in str(analogs_raw).split(",") if str(aid).strip()]
                        created_count = 0
                        for analog_id in analog_ids:
                            query = select(Analog).where(
                                (Analog.good_id == good_id) & (Analog.analog_good_id == analog_id)
                            )
                            result = await session.execute(query)
                            if not result.scalars().first():
                                analog = Analog(good_id=good_id, analog_good_id=analog_id)
                                session.add(analog)
                                created_count += 1
                                stats["analogs_created"] += 1
                        if created_count:
                            logger.debug(f"ANALOGS: GoodID={good_id} создано {created_count}")

                    # Обработка цен в валюте (если есть)
                    if currency_id and (row_get(row_idx, "EqualSalePrice") or row_get(row_idx, "EqualWholesalePrice")):
                        query = select(ProductCurrencyPrice).where(
                            (ProductCurrencyPrice.good_id == good_id) & 
                            (ProductCurrencyPrice.currency_id == currency_id)
                        )
                        result = await session.execute(query)
                        price = result.scalars().first()
                        price_data = {
                            "retail_price": parse_float(row_get(row_idx, "EqualSalePrice")),
                            "wholesale_price": parse_float(row_get(row_idx, "EqualWholesalePrice")),
                        }
                        if price:
                            for key, value in price_data.items():
                                setattr(price, key, value)
                        else:
                            price = ProductCurrencyPrice(
                                good_id=good_id,
                                currency_id=currency_id,
                                **price_data
                            )
                            session.add(price)
                            stats["currency_prices_created"] += 1

                    # Коммитим батч каждые commit_batch_size строк
                    if processed_rows % commit_batch_size == 0:
                        try:
                            await session.commit()
                            logger.info(f"Коммит батча: {processed_rows} строк")
                        except Exception as e:
                            logger.error(f"Ошибка при коммите батча: {str(e)}")
                            await session.rollback()
                            continue

                except Exception as e:
                    logger.error(f"Ошибка при обработке строки {processed_rows}: {str(e)}")
                    try:
                        await session.rollback()
                    except:
                        pass
                    continue

            # Коммитим оставшиеся изменения
            if processed_rows % commit_batch_size != 0:
                try:
                    await session.commit()
                    logger.info("Коммит финального батча завершён")
                except Exception as e:
                    logger.error(f"Ошибка при коммите финального батча: {str(e)}")
                    await session.rollback()

            # Закрываем сессию
            try:
                await session.close()
            except:
                pass

    except FileNotFoundError:
        logger.error("Файл torgsoft/TSGoods.csv не найден")
        return {"error": "Файл torgsoft/TSGoods.csv не найден"}
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {str(e)}")
        return {"error": f"Ошибка при синхронизации: {str(e)}"}
    
    logger.info(f"Синхронизирован {stats}")
    return stats