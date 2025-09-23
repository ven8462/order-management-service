PROJECT_NAME = order-management-service

# ===== Development =====
dev-up:
	docker compose -f docker-compose.dev.yml up --build -d

dev-down:
	docker compose -f docker-compose.dev.yml down -v

dev-logs:
	docker compose -f docker-compose.dev.yml logs -f app

dev-shell:
	docker compose -f docker-compose.dev.yml exec app bash


# ===== Testing =====
test-up:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

test-down:
	docker compose -f docker-compose.test.yml down -v

test-shell:
	docker compose -f docker-compose.test.yml run --rm app bash

# Run migrations/tests inside test container
migrate-test:
	docker compose -f docker-compose.test.yml run --rm app poetry run python manage.py migrate --noinput

test:
	docker compose -f docker-compose.test.yml run --rm app poetry run python manage.py test --noinput


# ===== Production =====
prod-up:
	docker compose -f docker-compose.prod.yml up --build -d

prod-down:
	docker compose -f docker-compose.prod.yml down -v

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f app

prod-shell:
	docker compose -f docker-compose.prod.yml exec app bash
