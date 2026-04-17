#!/bin/bash

# 1. Exit immediately if a command fails
set -e

echo "Preparing test environment..."

# 2. Get the absolute path of the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 3. Start only  infrastructure
docker-compose -f docker/docker-compose.yml up -d db redis --wait

echo "Running migrations..."
alembic upgrade head

echo "Database is up. Running migrations/tests..."


# 4. Run pytest
set +e
pytest
TEST_EXIT_CODE=$?
set -e

# 5. Cleanup
echo "Cleaning up..."
docker-compose -f docker/docker-compose.yml down

# 6. Exit with the same code pytest gave us
exit $TEST_EXIT_CODE