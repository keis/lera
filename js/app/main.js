define([
    './status',
    './socket',
    './session',
    './view'
], function (setStatus, Socket, session, View) {
    'use strict';

    function start () {
        var sock = new Socket('ws://localhost:8888/socket'),
            view;

        view = new View({
            el: $('#container'),
            socket: sock
        });

        try {
            session.resume(sock);
        } catch (err) {
            console.log("Could not resume session");
            session.watch(sock);
        }

        setStatus('connecting');

        sock.on('close', function () {
            setStatus('error', 'disconnected');
        });

        sock.on('open', function () {
            setStatus('connected');
        });
    }

    return {
        start: start
    };
});
