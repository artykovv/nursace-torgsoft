from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from config.nursace_database import Base

class Collection(Base):
    __tablename__ = 'collections'
    
    collection_id = Column(Integer, primary_key=True)
    collection_name = Column(String(255), nullable=False)
    parent_collection_id = Column(Integer, ForeignKey('collections.collection_id'))
    manufacturer_id = Column(Integer, ForeignKey('manufacturers.manufacturer_id'))
    
    parent = relationship("Collection", remote_side=[collection_id], back_populates="children")
    children = relationship("Collection", back_populates="parent")
    manufacturer = relationship("Manufacturer", back_populates="collections")
    products = relationship("Product", back_populates="collection")