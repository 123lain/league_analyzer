Feature-wise не закончил, на основном апи только один эндпоинт на поиск по Riot ID. Разделил работу между нашим апи и Riot API на несколько слоев: analyzer.api.main - analyzer.services.ingestion - analyzer.core.riot_lient. 
Напрямую с бд работает analyzer.database.repository.
Написал кастомный логгер analyzer.core.logger.
Bucket реализовал в analyzer.core.rate_limiter, с адаптацией под headers лимиты от riot.
Если выбирать глубину истории матчей, то думаю 20? Как лимит токена 

# Запуск
docker compose up --build 
из корня
# Миграции

alembic revision --autogenerate -m 'сообщение'
alembic upgrade head
из корня

# Примеры запуска
<img width="1781" height="353" alt="image" src="https://github.com/user-attachments/assets/aca8a0ed-03bc-4105-ab79-792f2c946c54" />
<img width="1499" height="925" alt="image" src="https://github.com/user-attachments/assets/b99d7549-f58f-4c34-a6ed-9872bdfd24b5" />
