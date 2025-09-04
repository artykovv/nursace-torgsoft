from typing import AsyncGenerator
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import NURSACE_DB_HOST, NURSACE_DB_NAME, NURSACE_DB_PASS, NURSACE_DB_PORT, NURSACE_DB_USER

DATABASE_URL = f"postgresql+asyncpg://{NURSACE_DB_USER}:{NURSACE_DB_PASS}@{NURSACE_DB_HOST}:{NURSACE_DB_PORT}/{NURSACE_DB_NAME}"
Base = declarative_base()

engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
   async with async_session_maker() as session:
       yield session