from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from config.marella_database import Base

class Category(Base):
    __tablename__ = 'categories'
    
    category_id = Column(Integer, primary_key=True)
    category_name = Column(String(255), nullable=False)
    parent_category_id = Column(Integer, ForeignKey('categories.category_id'))
    synchronization_section = Column(String(255))
    good_type_name = Column(String(255))
    
    parent = relationship("Category", remote_side=[category_id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    products = relationship("Product", back_populates="category")