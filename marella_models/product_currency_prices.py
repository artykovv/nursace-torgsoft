from sqlalchemy import Column, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from config.marella_database import Base

class ProductCurrencyPrice(Base):
    __tablename__ = 'product_currency_prices'
    
    price_id = Column(Integer, primary_key=True)
    good_id = Column(Integer, ForeignKey('products.good_id'))
    currency_id = Column(Integer, ForeignKey('currencies.currency_id'))
    retail_price = Column(Float)
    wholesale_price = Column(Float)
    
    product = relationship("Product", back_populates="currency_prices")
    currency = relationship("Currency", back_populates="prices")