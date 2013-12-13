/**
 * A wrapper around the builtin WebSocket to provide automatic reconnect
 * and backbone style events.
 */

define(['backbone', 'underscore'], function (Backbone, _) {
    'use strict';

    function Socket (url) {
        var self = this,
            attempt = 1,
            sock;

        function connect() {
            sock = new WebSocket(url);
            sock.onmessage = onmessage;
            sock.onopen = onopen;
            sock.onclose = onclose;
        }

        function onmessage(event) {
            self.trigger('data', JSON.parse(event.data));
        };

        function onopen(event) {
            self.trigger('open');
            attempt = 1;
        }

        function onclose(event) {
            self.trigger('close');
            attempt += 1;
            setTimeout(connect, 500 * Math.min(attempt, 10));
        };

        this._send = function send(data) {
            sock.send(data);
        };

        this._close = function close() {
            sock.close();
        }

        connect();
    };

    Socket.prototype.send = function send(data) {
        this.trigger('send', data);
        this._send(data);
    }

    Socket.prototype.hup = function hup() {
        this._close()
    }

    _.extend(Socket.prototype, Backbone.Events);

    return Socket;
});
