from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from config.nursace_database import Base

class Analog(Base):
    __tablename__ = 'analogs'
    
    analog_id = Column(Integer, primary_key=True)
    good_id = Column(Integer, ForeignKey('products.good_id'))
    analog_good_id = Column(Integer, ForeignKey('products.good_id'))
    
    product = relationship("Product", foreign_keys=[good_id], back_populates="analogs")
    analog_product = relationship("Product", foreign_keys=[analog_good_id], back_populates="analog_products")