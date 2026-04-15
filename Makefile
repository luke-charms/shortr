run:
	uvicorn app.main:app --reload

test:
	pytest

docker:
	docker compose -f docker/docker-compose.yml up --build