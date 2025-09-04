from typing import AsyncGenerator
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import MARELLA_DB_HOST, MARELLA_DB_NAME, MARELLA_DB_PASS, MARELLA_DB_PORT, MARELLA_DB_USER

DATABASE_URL = f"postgresql+asyncpg://{MARELLA_DB_USER}:{MARELLA_DB_PASS}@{MARELLA_DB_HOST}:{MARELLA_DB_PORT}/{MARELLA_DB_NAME}"
Base = declarative_base()

engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
   async with async_session_maker() as session:
       yield session