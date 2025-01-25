docker-compose -p prod -f docker-compose.yaml up -d --build
docker-compose -p prod -f docker-compose.yaml down -v


docker-compose -f docker-compose.test.yaml --env-file=.env.test -p prod_test up --build --abort-on-container-exit
docker-compose -f docker-compose.test.yaml --env-file=.env.test -p prod_test down -v