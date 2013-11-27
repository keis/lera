VIRTUALENV=virtualenv -p python3.3
VIRTUAL=. env/bin/activate;

.PHONY: env start-server create-world

env: env/bin/activate env/freeze.txt

env/bin/activate:
	${VIRTUALENV} env

env/freeze.txt: env/bin/activate

env/freeze.txt: requirements.txt
	${VIRTUAL} pip install -r requirements.txt
	${VIRTUAL} pip freeze > $@

start-server: env/freeze.txt
	${VIRTUAL} python -m lera

node_modules/.bin/riak-genesis node_modules/.bin/coffee:
	mkdir -p node_modules
	npm install riak-genesis coffee-script

create-world: node_modules/.bin/riak-genesis node_modules/.bin/coffee
create-world: world.coffee
	node_modules/.bin/riak-genesis ${RIAK} $< -v
