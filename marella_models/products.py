from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from config.marella_database import Base

class Product(Base):
    __tablename__ = 'products'

    good_id = Column(Integer, primary_key=True, index=True)
    good_name = Column(String(500), nullable=False)
    short_name = Column(String(255))
    description = Column(String(255))
    articul = Column(String(30))
    barcode = Column(String(40))
    retail_price = Column(Float)
    wholesale_price = Column(Float)
    retail_price_with_discount = Column(Float)
    prime_cost = Column(Float)
    equal_sale_price = Column(Float)
    equal_wholesale_price = Column(Float)
    price_discount_percent = Column(Float)
    min_quantity_for_order = Column(Integer)
    wholesale_count = Column(Float)
    warehouse_quantity = Column(Float)
    measure = Column(Float)
    height = Column(Float)
    width = Column(Float)
    display = Column(Integer)  # 0 - не отображать, 1 - отображать
    closeout = Column(Integer)  # 0 - не уценка, 1 - уценка
    guarantee_period = Column(Integer)
    category_id = Column(Integer, ForeignKey('categories.category_id'), nullable=True)
    manufacturer_id = Column(Integer, ForeignKey('manufacturers.manufacturer_id'), nullable=False)
    collection_id = Column(Integer, ForeignKey('collections.collection_id'), nullable=True)
    season_id = Column(Integer, ForeignKey('seasons.season_id'), nullable=False)
    sex_id = Column(Integer, ForeignKey('sexes.sex_id'), nullable=False)
    color_id = Column(Integer, ForeignKey('colors.color_id'), nullable=True)
    material_id = Column(Integer, ForeignKey('materials.material_id'), nullable=False)
    measure_unit_id = Column(Integer, ForeignKey('measure_units.measure_unit_id'), nullable=False)
    guarantee_mes_unit_id = Column(Integer, ForeignKey('measure_units.measure_unit_id'), nullable=False)
    supplier_code = Column(String(255))
    model_good_id = Column(Integer)
    pack = Column(String(255))
    pack_size = Column(String(255))
    power_supply = Column(String(255))
    count_units_per_box = Column(String(255))
    age = Column(String(255))
    product_size = Column(String(255))  # TheSize из CSV - строковое значение
    fashion_name = Column(String(255))  # FashionName из CSV
    # good_type_full = Column(String(255))  # GoodTypeFull из CSV
    # producer_collection_full = Column(String(255))  # ProducerCollectionFull из CSV
    retail_price_per_unit = Column(Float)  # RetailPricePerUnit из CSV
    wholesale_price_per_unit = Column(Float)  # WholesalePricePerUnit из CSV
    
    category = relationship("Category", back_populates="products")
    # custom_categories = relationship("CustomCategory",secondary=product_custom_category, back_populates="products")
    manufacturer = relationship("Manufacturer", back_populates="products")
    collection = relationship("Collection", back_populates="products")
    season = relationship("Season", back_populates="products")
    sex = relationship("Sex", back_populates="products")
    color = relationship("Color", back_populates="products")
    material = relationship("Material", back_populates="products")
    measure_unit = relationship("MeasureUnit", foreign_keys=[measure_unit_id], back_populates="products_measure")
    guarantee_mes_unit = relationship("MeasureUnit", foreign_keys=[guarantee_mes_unit_id], back_populates="products_guarantee")
    attributes = relationship("ProductAttribute", back_populates="product")
    currency_prices = relationship("ProductCurrencyPrice", back_populates="product")
    analogs = relationship("Analog", foreign_keys="Analog.good_id", back_populates="product")
    analog_products = relationship("Analog", foreign_keys="Analog.analog_good_id", back_populates="analog_product")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

    # lead_products = relationship("LeadProduct", back_populates="product")
    # discounts = relationship("DiscountProduct", back_populates="product")
    # outlets = relationship("OutletProduct", back_populates="product")