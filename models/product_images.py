from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from config.base_class import Base

class ProductImage(Base):
    __tablename__ = 'product_images'

    image_id = Column(Integer, primary_key=True)
    good_id = Column(Integer, ForeignKey('products.good_id'), nullable=False)
    image_url = Column(String(500), nullable=False)  # Путь к файлу или URL изображения
    is_main = Column(Boolean, default=False, nullable=False)  # Флаг главного изображения
    order = Column(Integer, default=0)  # Порядок отображения (опционально)

    product = relationship("Product", back_populates="images")