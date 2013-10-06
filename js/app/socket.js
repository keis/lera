define(['backbone', 'underscore'], function (Backbone, _) {
    'use strict';

    function Socket (url) {
        var self = {},
            sock = new WebSocket(url);

        _.extend(self, Backbone.Events);

        function reconnect() {
            sock = new WebSocket(url);
            attach(sock);
        }

        function onmessage(event) {
            self.trigger('recv', JSON.parse(event.data));
        };

        function onopen(event) {
            self.trigger('open');
        }

        function onclose(event) {
            self.trigger('close');
            setTimeout(reconnect, 500);
        };

        function attach(s) {
            s.onmessage = onmessage;
            s.onopen = onopen;
            s.onclose = onclose;
        }

        self.send = function (data) {
            self.trigger('send', data);
            sock.send(data);
        }

        attach(sock);

        return self;
    };

    return Socket;
});
