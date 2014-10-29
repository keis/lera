define([
    './status',
    './socket',
    './session',
    './view'
], function (setStatus, Socket, session, View) {
    'use strict';

    function start () {
        var host = window.location.host,
            sock = new Socket('ws://' + host + '/socket'),
            view;

        view = new View({
            el: $('body'),
            socket: sock
        });

        $('#status').on('click', '[data-action="logout"]', function () {
            session.forget();
            sock.hup();
        });

        setStatus('connecting');

        sock.on('close', function () {
            setStatus('error', 'disconnected');
        });

        sock.on('open', function () {
            try {
                session.resume(sock);
            } catch (err) {
                console.log("Could not resume session", err);
                session.watch(sock);
            }

            setStatus('connected');
        });
    }

    return {
        start: start
    };
});
