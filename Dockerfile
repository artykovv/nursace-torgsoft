FROM python:3.11

# Установка зависимостей
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Копирование .env, если он есть (опционально, иначе пробрасывать через docker run)
COPY .env .

# Открываем порт для FastAPI
EXPOSE 8000

# Запуск приложения через uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 