VIRTUALENV=virtualenv -p python3.3
VIRTUAL=. env/bin/activate;
RIAK_GENESIS=node_modules/.bin/riak-genesis
BOWER=node_modules/.bin/bower
COFFEE=node_modules/.bin/coffee

.PHONY: env start-server create-world

env: env/bin/activate env/freeze.txt

env/bin/activate:
	${VIRTUALENV} env

env/freeze.txt: env/bin/activate

env/freeze.txt: requirements.txt
	${VIRTUAL} pip install -r requirements.txt
	${VIRTUAL} pip freeze > $@

start-server: env/freeze.txt bower_components
	${VIRTUAL} python -m lera

bower_components: node_modules/.bin/bower
bower_components: bower.json
	$(BOWER) install

${RIAK_GENESIS} ${BOWER} ${COFFEE}:
	mkdir -p node_modules
	npm install riak-genesis coffee-script bower

create-world: ${RIAK_GENESIS} ${COFFE}
create-world: world.coffee
	node_modules/.bin/riak-genesis ${RIAK} $< -v
