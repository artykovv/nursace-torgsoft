from sqlalchemy import Column,  Integer,  String
from sqlalchemy.orm import relationship
from config.nursace_database import Base

class MeasureUnit(Base):
    __tablename__ = 'measure_units'
    
    measure_unit_id = Column(Integer, primary_key=True)
    unit_name = Column(String(255), nullable=False)
    
    products_measure = relationship("Product", foreign_keys="Product.measure_unit_id", back_populates="measure_unit")
    products_guarantee = relationship("Product", foreign_keys="Product.guarantee_mes_unit_id", back_populates="guarantee_mes_unit")