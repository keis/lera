define([
    './status',
    './socket',
    './socket',
    'backbone',
    'underscore',
    'jquery'
], function (setStatus, Socket, Backbone, _, $) {
    'use strict';

    var sock = new Socket('ws://localhost:8888/socket'),
        form = document.querySelector('form[name=command]'),
        commandInput = form.querySelector('input[name=command]'),
        messages = document.querySelector('#messages'),
        user = {},
        loggedIn = false,
        prompt,
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
        showMessage(message, true);
        sock.send(message);

        if (!loggedIn && prompt) {
            console.log('message during login', message);
            if (prompt.match(/name$/)) {
                user.name = message;
            } else if (prompt.match(/quest$/)) {
                user.quest = message;
            }
        }
    }

    function loadUserData () {
        var data = window.localStorage['user'];
        if (data) {
            try {
                user = JSON.parse(data);
            } catch (err) {
                console.log(err);
            }
        }
        console.log('user information', user);
    }

    function saveUserData () {
        console.log('saving user information', user);
        window.localStorage['user'] = JSON.stringify(user);
    }

    loadUserData();
    setStatus('connecting');
    commandInput.disabled = true;

    sock.on('recv', function (data) {
        prompt = data.prompt || '';

        console.log('message', data);
        showMessage(data.message);
        commandInput.disabled = (prompt === '<disabled>')
        commandInput.placeholder = prompt;

        if (!loggedIn && user.name && user.quest) {
            if (prompt.match(/name$/)) {
                sendMessage(user.name);
            } else if (prompt.match(/quest$/)) {
                sendMessage(user.quest);
            } else if (data.message.match(/welcome/i)) {
                loggedIn = true;
                saveUserData();
            }
        }
    });

    sock.on('close', function () {
        setStatus('error', 'disconnected');
        loggedIn = false,
        commandInput.disabled = true;
    });

    sock.on('open', function () {
        setStatus('connected');
        loggedIn = false,
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
