from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from config.base_class import Base

class Color(Base):
    __tablename__ = 'colors'
    
    color_id = Column(Integer, primary_key=True)
    color_name = Column(String(50), nullable=False)
    
    products = relationship("Product", back_populates="color")