from sqlalchemy import Column,  Integer,  String
from sqlalchemy.orm import relationship
from config.nursace_database import Base

class Currency(Base):
    __tablename__ = 'currencies'
    
    currency_id = Column(Integer, primary_key=True)
    currency_name = Column(String(50), nullable=False)
    
    prices = relationship("ProductCurrencyPrice", back_populates="currency")