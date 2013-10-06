define(['backbone', 'underscore'], function (Backbone, _) {
    'use strict';

    function Socket (url) {
        var self = {},
            sock = new WebSocket(url);

        _.extend(self, Backbone.Events);

        sock.onmessage = function (event) {
            self.trigger('recv', JSON.parse(event.data));
        };

        sock.onopen = function (event) {
            self.trigger('open');
        }

        sock.onclose = function (event) {
            self.trigger('close');
        };

        self.send = function (data) {
            self.trigger('send', data);
            sock.send(data);
        }

        return self;
    };

    return Socket;
});
