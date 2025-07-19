import csv
import logging
import aiofiles
from sqlalchemy.future import select
from models import (
    Product, Category, Manufacturer, Collection, Season, Sex, Color, Material,
    MeasureUnit, Currency, ProductCurrencyPrice, Analog
)
from config.database import async_session_maker

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_int(value: str) -> int | None:
    if not value or not value.strip():
        return None
    try:
        return int(value.strip())
    except ValueError:
        logger.warning(f"Не удалось преобразовать в int: {value}")
        return None
    
def parse_float(value: str) -> float | None:
    if not value or not value.strip():
        return None
    try:
        return float(value.replace(",", ".").strip())
    except ValueError:
        logger.warning(f"Не удалось преобразовать в float: {value}")
        return None

async def sync_torgsoft_csv() -> dict:
    async with async_session_maker() as session:
        """
        Синхронизирует данные из CSV-файла Торгсофт (torgsoft/TSGoods.csv) с базой данных.

        Args:
            session: Асинхронная сессия SQLAlchemy.

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
            "colors_created": 0,
            "materials_created": 0,
            "measure_units_created": 0,
            "currencies_created": 0,
            "attributes_created": 0,
            "currency_prices_created": 0,
            "analogs_created": 0,
        }

        async def get_or_create(model, filter_field, filter_value, defaults=None):
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
            except Exception as e:
                logger.error(f"Ошибка в get_or_create для {model.__name__}, поле {filter_field}: {str(e)}")
                raise

        async def get_or_create_hierarchy(model, parent_field, name_field, names, parent_id=None, defaults=None):
            """Обрабатывает иерархию (например, для категорий или коллекций)."""
            try:
                current_parent_id = parent_id
                last_instance = None
                for name in names:
                    instance, created = await get_or_create(
                        model,
                        name_field,
                        name,
                        defaults={parent_field: current_parent_id, **(defaults or {})}
                    )
                    if created:
                        stats[f"{model.__tablename__}_created"] += 1
                    last_instance = instance
                    # Явно указываем правильное имя идентификатора
                    id_field = 'category_id' if model.__name__ == 'Category' else 'collection_id' if model.__name__ == 'Collection' else 'id'
                    current_parent_id = getattr(instance, id_field)
                return last_instance
            except Exception as e:
                logger.error(f"Ошибка в get_or_create_hierarchy для {model.__name__}: {str(e)}")
                raise

        # Чтение CSV-файла
        try:
            async with aiofiles.open("shared_files/TSGoods.csv", mode="r", encoding="utf-8") as csv_file:
            # async with aiofiles.open("torgsoft/TSGoods.csv", mode="r", encoding="utf-8") as csv_file:
                content = await csv_file.read()
                reader = csv.DictReader(content.splitlines(), delimiter=",")

                for row in reader:
                    # Обработка справочных данных
                    # Категории (GoodTypeFull)
                    category_id = None
                    if row.get("GoodTypeFull"):
                        category_names = [name.strip() for name in row["GoodTypeFull"].split(",") if name.strip()]
                        try:
                            category = await get_or_create_hierarchy(
                                Category, "parent_category_id", "category_name", category_names,
                                defaults={"synchronization_section": category_names[0] if category_names else None}
                            )
                            category_id = category.category_id if category else None
                            logger.debug(f"Категория обработана: {category_names}, category_id={category_id}")
                        except Exception as e:
                            logger.error(f"Ошибка при обработке категорий {category_names}: {str(e)}")
                            continue  # Пропускаем товар, если ошибка в категориях

                    # Производитель и страна
                    manufacturer_name = row.get("Country") or "Unknown"
                    manufacturer, created = await get_or_create(
                        Manufacturer, "manufacturer_name", manufacturer_name,
                        defaults={"country": manufacturer_name}
                    )
                    if created:
                        stats["manufacturers_created"] += 1

                    # Коллекции (ProducerCollectionFull)
                    if row.get("ProducerCollectionFull"):
                        collection_names = [name.strip() for name in row["ProducerCollectionFull"].split(",") if name.strip()]
                        collection = await get_or_create_hierarchy(
                            Collection, "parent_collection_id", "collection_name", collection_names,
                            defaults={"manufacturer_id": manufacturer.manufacturer_id}
                        )
                        collection_id = collection.collection_id if collection else None
                    else:
                        collection_id = None

                    # Сезон
                    season_name = row.get("Season") or "Unknown"
                    season, created = await get_or_create(Season, "season_name", season_name)
                    if created:
                        stats["seasons_created"] += 1

                    # Пол
                    sex_value = int(row.get("Sex", 0))
                    sex_mapping = {
                        0: "Не определен",
                        1: "Мужской",
                        2: "Женский",
                        3: "Мальчик",
                        4: "Девочка",
                        5: "Унисекс"
                    }
                    sex_name = sex_mapping.get(sex_value, "Не определен")
                    sex, created = await get_or_create(Sex, "sex_name", sex_name)
                    if created:
                        stats["sexes_created"] += 1

                    # Цвет
                    color_name = row.get("Color") or "Unknown"
                    color, created = await get_or_create(Color, "color_name", color_name)
                    if created:
                        stats["colors_created"] += 1

                    # Материал
                    material_name = row.get("Material") or "Unknown"
                    material, created = await get_or_create(Material, "material_name", material_name)
                    if created:
                        stats["materials_created"] += 1

                    # Единица измерения
                    measure_unit_name = row.get("MeasureUnit") or "Unknown"
                    measure_unit, created = await get_or_create(MeasureUnit, "unit_name", measure_unit_name)
                    if created:
                        stats["measure_units_created"] += 1

                    # Валюта (если есть EqualCurrencyName)
                    currency_name = row.get("EqualCurrencyName") or None
                    currency_id = None
                    if currency_name:
                        currency, created = await get_or_create(Currency, "currency_name", currency_name)
                        if created:
                            stats["currencies_created"] += 1
                        currency_id = currency.currency_id

                    # Товар
                    good_id = int(row["GoodID"])
                    query = select(Product).where(Product.good_id == good_id)
                    result = await session.execute(query)
                    product = result.scalars().first()

                    product_data = {
                        "good_name": row.get("GoodName"),
                        "short_name": row.get("ShortName") or None,
                        "description": row.get("Description") or None,
                        "articul": row.get("Articul") or None,
                        "barcode": row.get("Barcode") or None,
                        "retail_price": parse_float(row.get("RetailPrice")),
                        "wholesale_price": parse_float(row.get("WholesalePrice")),
                        "retail_price_with_discount": parse_float(row.get("RetailPriceWithDiscount")),
                        "prime_cost": parse_float(row.get("PrimeCost")),
                        "equal_sale_price": parse_float(row.get("EqualSalePrice")),
                        "equal_wholesale_price": parse_float(row.get("EqualWholesalePrice")),
                        "price_discount_percent": parse_float(row.get("PriceDiscountPercent")),
                        "min_quantity_for_order": parse_int(row.get("MinQuantityForOrder")),
                        "wholesale_count": parse_float(row.get("WholesaleCount")),
                        "warehouse_quantity": parse_float(row.get("WarehouseQuantity")),
                        "measure": parse_float(row.get("Measure")),
                        "height": parse_float(row.get("Height")),
                        "width": parse_float(row.get("Width")),
                        "display": parse_int(row.get("Display")),
                        "closeout": parse_int(row.get("Closeout")),
                        "category_id": category_id,
                        "manufacturer_id": manufacturer.manufacturer_id,
                        "collection_id": collection_id,
                        "season_id": season.season_id,
                        "sex_id": sex.sex_id,
                        "color_id": color.color_id,
                        "material_id": material.material_id,
                        "measure_unit_id": measure_unit.measure_unit_id,
                        "guarantee_mes_unit_id": measure_unit.measure_unit_id,
                        "supplier_code": row.get("SupplierCode") or None,
                        "model_good_id": parse_int(row.get("Category")) if row.get("Category") != "-1" else None,
                        "pack": row.get("Pack") or None,
                        "pack_size": row.get("PackSize") or None,
                        "power_supply": row.get("PowerSupply") or None,
                        "count_units_per_box": row.get("CountUnitsPerBox") or None,
                        "age": row.get("Age") or None,
                        "product_size": parse_float(row.get("TheSize")),
                        "fashion_name": row.get("FashionName") or None,
                        "retail_price_per_unit": parse_float(row.get("RetailPricePerUnit")),
                        "wholesale_price_per_unit": parse_float(row.get("WholesalePricePerUnit")),
                    }

                    if product:
                        # Обновление существующего товара
                        for key, value in product_data.items():
                            setattr(product, key, value)
                        stats["products_updated"] += 1
                    else:
                        # Создание нового товара
                        product = Product(good_id=good_id, **product_data)
                        session.add(product)
                        stats["products_created"] += 1

                    # Обработка аналогов
                    if row.get("Analogs"):
                        analog_ids = [int(aid) for aid in row["Analogs"].split(",") if aid.strip()]
                        for analog_id in analog_ids:
                            query = select(Analog).where(
                                (Analog.good_id == good_id) & (Analog.analog_good_id == analog_id)
                            )
                            result = await session.execute(query)
                            if not result.scalars().first():
                                analog = Analog(good_id=good_id, analog_good_id=analog_id)
                                session.add(analog)
                                stats["analogs_created"] += 1

                    # Обработка цен в валюте (если есть)
                    if currency_id and (row.get("EqualSalePrice") or row.get("EqualWholesalePrice")):
                        query = select(ProductCurrencyPrice).where(
                            (ProductCurrencyPrice.good_id == good_id) & 
                            (ProductCurrencyPrice.currency_id == currency_id)
                        )
                        result = await session.execute(query)
                        price = result.scalars().first()
                        price_data = {
                            "retail_price": parse_float(row.get("EqualSalePrice")),
                            "wholesale_price": parse_float(row.get("EqualWholesalePrice")),
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

            # Коммит изменений
            await session.commit()
        except FileNotFoundError:
            logger.error("Файл torgsoft/TSGoods.csv не найден")
            return {"error": "Файл torgsoft/TSGoods.csv не найден"}
        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {str(e)}")
            await session.rollback()
            return {"error": f"Ошибка при синхронизации: {str(e)}"}
        
        logger.info(f"Синхронизирован {stats}")
        return stats