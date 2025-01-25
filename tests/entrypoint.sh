#!/bin/sh

# Добавляем путь текущей директории в PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

# Убедитесь, что база данных доступна
echo "Ожидание доступности базы данных..."
while ! pg_isready -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USERNAME}; do
    sleep 1
done

echo "База данных доступна. Запуск тестов..."

# Запуск pytest с логированием
pytest ./src --disable-warnings -s --log-cli-level=INFO
# pytest ./src/test_06_business_promo_id_valid.tavern.yml --disable-warnings -s --log-cli-level=INFO