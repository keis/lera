VIRTUALENV=virtualenv -p python3.3
VIRTUAL=. env/bin/activate;

.PHONY: start-server

env/bin/activate:
	${VIRTUALENV} env

env/freeze.txt: env/bin/activate

env/freeze.txt: requirements.txt
	${VIRTUAL} pip install -r requirements.txt
	${VIRTUAL} pip freeze > $@

start-server: env/freeze.txt
	${VIRTUAL} python server.py
