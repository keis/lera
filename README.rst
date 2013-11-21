A multiuser dungeon project
===========================

A project to explore all things RIAK, WebSockets and dungeoneering.

Getting started
---------------

prerequisites:

* riak
* npm
* virtualenv
* make
* bower (npm install -g bower)

After getting the system requirements in place the setup is a mostly
automated process.

* Setup up virtualenv for python
    make env

    This will create a virtualenv for python and install the packages the
    server needs to run as specified in `requirements.txt`

* Install web assests
    bower install

    Install the various javascript libraries the web-client uses.

* Populate riak with world data
    make create-world

    Uses `riak-genesis <http://github.com/keis/riak-genesis>`_ to configure the
    database with a world as described in `world.coffee`

* Start the server
    make start-server

* Visit localhost:8888
    *fingers crossed*
