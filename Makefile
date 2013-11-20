VIRTUALENV=virtualenv -p python3.3
VIRTUAL=. env/bin/activate;

.PHONY: start-server create-world

env/bin/activate:
	${VIRTUALENV} env

env/freeze.txt: env/bin/activate

env/freeze.txt: requirements.txt
	${VIRTUAL} pip install -r requirements.txt
	${VIRTUAL} pip freeze > $@

start-server: env/freeze.txt
	${VIRTUAL} python server.py

node_modules/.bin/riak-genesis node_modules/.bin/coffee:
	npm install riak-genesis coffee-script

.world: node_modules/.bin/riak-genesis node_modules/.bin/coffee
.world: world.coffee
	node_modules/.bin/riak-genesis ${RIAK} $< -v
	touch $@

create-world: .world

