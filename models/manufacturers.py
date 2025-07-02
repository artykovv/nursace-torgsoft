from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from config.base_class import Base

class Manufacturer(Base):
    __tablename__ = 'manufacturers'
    
    manufacturer_id = Column(Integer, primary_key=True)
    manufacturer_name = Column(String(100), nullable=False)
    country = Column(String(100))
    
    products = relationship("Product", back_populates="manufacturer")
    collections = relationship("Collection", back_populates="manufacturer")