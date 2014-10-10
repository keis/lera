VIRTUALENV=virtualenv -p python3.3
VIRTUAL=. env/bin/activate;
RIAK_GENESIS=node_modules/.bin/riak-genesis
BOWER=node_modules/.bin/bower
COFFEE=node_modules/.bin/coffee

.PHONY: env start-server create-world test

env: env/bin/activate env/freeze.txt

test: tmp/xunit.xml tmp/coverage.xml

env/bin/activate:
	${VIRTUALENV} env

env/freeze.txt: env/bin/activate
env/freeze.txt: requirements.txt
	${VIRTUAL} pip install -r $<
	${VIRTUAL} pip freeze > $@

env/freeze-test.txt: env/bin/activate
env/freeze-test.txt: test-requirements.txt
	${VIRTUAL} pip install -r $<
	${VIRTUAL} pip freeze > $@

start-server: env/freeze.txt bower_components
	${VIRTUAL} python -m lera

bower_components: node_modules/.bin/bower
bower_components: bower.json
	$(BOWER) install

tmp:
	mkdir -p $@

tmp/xunit.xml tmp/coverage.xml: tmp env/freeze.txt env/freeze-test.txt
	$(VIRTUAL) nosetests --with-xunit --xunit-file=tmp/xunit.xml --with-coverage --cover-xml --cover-xml-file=tmp/coverage.xml --cover-inclusive --cover-erase --cover-package lera tests

${RIAK_GENESIS} ${BOWER} ${COFFEE}:
	mkdir -p node_modules
	npm install riak-genesis coffee-script bower

create-world: ${RIAK_GENESIS} ${COFFE}
create-world: world.coffee
	node_modules/.bin/riak-genesis ${RIAK} $< -v
