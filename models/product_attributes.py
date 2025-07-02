from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from config.base_class import Base

class ProductAttribute(Base):
    __tablename__ = 'product_attributes'
    
    attribute_id = Column(Integer, primary_key=True)
    good_id = Column(Integer, ForeignKey('products.good_id'))
    attribute_name = Column(String(255), nullable=False)
    attribute_value = Column(String(1000))
    
    product = relationship("Product", back_populates="attributes")