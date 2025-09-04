from sqlalchemy import Column,  Integer,  String
from sqlalchemy.orm import relationship
from config.marella_database import Base

class Material(Base):
    __tablename__ = 'materials'
    
    material_id = Column(Integer, primary_key=True)
    material_name = Column(String(200), nullable=False)
    products = relationship("Product", back_populates="material")