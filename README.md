Разделил работу между нашим апи и Riot API на несколько слоев: analyzer.api.main - analyzer.services.ingestion - analyzer.core.riot_lient. 
Напрямую с бд работает analyzer.database.repository.
Написал кастомный логгер analyzer.core.logger.
Bucket реализовал в analyzer.core.rate_limiter, с адаптацией под headers лимиты от riot.
Если выбирать глубину истории матчей, то думаю 20? Как лимит токена 


# Запуск

docker compose up 


# Миграции

alembic revision --autogenerate 
alembic upgrade head
из корня


# Примеры запуска

Профиль игрока по riot id
<img width="1444" height="907" alt="image" src="https://github.com/user-attachments/assets/c678c4a4-99de-426c-b4c6-240c1454e444" />

Матчи игрока по puuid
<img width="1376" height="1074" alt="image" src="https://github.com/user-attachments/assets/326f3862-dcd0-4a99-8426-6ec0cd52a37a" />

Стата игрока на чемпионах:
<img width="1376" height="1074" alt="image" src="https://github.com/user-attachments/assets/c234172e-c0c1-4ef8-9d89-19233a98d83e" />
