from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from config.nursace_database import Base

class Season(Base):
    __tablename__ = 'seasons'
    
    season_id = Column(Integer, primary_key=True)
    season_name = Column(String(100), nullable=False)
    
    products = relationship("Product", back_populates="season")