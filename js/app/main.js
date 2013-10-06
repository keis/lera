define([
    './status',
    './socket',
    './session',
], function (setStatus, Socket, session) {
    'use strict';

    var sock = new Socket('ws://localhost:8888/socket'),
        form = document.querySelector('form[name=command]'),
        commandInput = form.querySelector('input[name=command]'),
        messages = document.querySelector('#messages'),
        setStatus;

    function showMessage (message, command) {
        var msg = document.createElement('p');
        msg.textContent = message;
        if (command) {
            msg.className = 'command';
        }
        messages.appendChild(msg);
    }

    function sendMessage (message) {
        sock.send(message);
    }

    try {
        session.resume(sock);
    } catch (err) {
        console.log("Could not resume session");
        session.watch(sock);
    }
    setStatus('connecting');
    commandInput.disabled = true;

    sock.on('recv', function (data) {
        prompt = data.prompt || '';

        console.log('message', data);
        showMessage(data.message);
        commandInput.disabled = (prompt === '<disabled>')
        commandInput.placeholder = prompt;
    });

    sock.on('send', function (message) {
        showMessage(message, true);
    });

    sock.on('close', function () {
        setStatus('error', 'disconnected');
        commandInput.disabled = true;
    });

    sock.on('open', function () {
        setStatus('connected');

        commandInput.disabled = false;
        commandInput.placeholder = '';
    });

    form.onsubmit = function (event) {
        var cmd = commandInput.value;
        event.preventDefault();
        if (cmd) {
            sendMessage(cmd);
            commandInput.value = '';
            commandInput.disabled = true;
        }
        return false;
    }

    return {
        start: function () {
        }
    };
});
