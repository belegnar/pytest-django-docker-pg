all: deps lint test

deps:
	@python3 -m pip install --upgrade pip && pip3 install -r requirements-dev.txt

black:
	@black --line-length 120 pytest_django_docker_pg tests

isort:
	@isort --line-length 120 --use-parentheses --multi-line 3 --combine-as --trailing-comma pytest_django_docker_pg tests

flake8:
	@flake8 --max-line-length 120 --ignore C901,C812,E203 --extend-ignore W503 pytest_django_docker_pg tests

pyright:
	@pyright pytest_django_docker_pg tests

lint: black isort flake8 pyright

test:
	@python3 -m pytest -vv --rootdir tests .

pyenv:
	echo pytest_django_docker_pg > .python-version && pyenv install -s 3.12.0 && pyenv virtualenv -f 3.12.0 pytest_django_docker_pg

pyenv-delete:
	pyenv virtualenv-delete -f pytest_django_docker_pg
