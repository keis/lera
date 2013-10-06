define(['backbone', 'jquery'], function (Backbone, $) {
    'use strict';

    return Backbone.View.extend({
        events: {
            'submit form[name=command]': 'sendCommand',
        },

        initialize: function (options) {
            this.socket = options.socket;
            this.$input = this.$('input[name=command]'),

            this.$input.prop('disabled', true);

            this.listenTo(this.socket, 'close', function () {
                this.$input.prop('disabled', true);
            });

            this.listenTo(this.socket, 'open', function () {
                this.$input.prop('disabled', true).prop('placeholder', '');
            });

            this.listenTo(this.socket, 'send', function (message) {
                this.showMessage(message, true);
            });

            this.listenTo(this.socket, 'recv', function (data) {
                var prompt = data.prompt || '';

                console.log('message', data);
                this.showMessage(data.message);
                this.$input.prop('disabled', prompt === '<disabled>');
                this.$input.prop('placeholder', prompt);
            });
        },

        showMessage: function (message, command) {
            var $msg = $('<p>');
            $msg.text(message);
            if (command) {
                $msg.addClass('command');
            }
            $msg.appendTo(this.$('#messages'));
        },

        sendCommand: function (event) {
            event.preventDefault();
            var cmd = this.$input.val();

            if (cmd) {
                this.socket.send(cmd);
                this.$input.val('').prop('disabled', true);
            }
            return false;
        }
    });
});
