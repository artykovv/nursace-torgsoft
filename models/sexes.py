from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from config.base_class import Base

class Sex(Base):
    __tablename__ = 'sexes'
    
    sex_id = Column(Integer, primary_key=True)
    sex_name = Column(String(50), nullable=False)  # 0 - не определен, 1 - мужской, и т.д.
    
    products = relationship("Product", back_populates="sex")