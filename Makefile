install:
	poetry install

valutatrade:
	poetry run valutatrade

build:
	poetry build

publish:
	poetry publish --dry-run

package-install:
	python3 -m pip install dist/*.whl

lint:
	poetry run ruff check .