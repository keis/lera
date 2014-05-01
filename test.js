var Client = require('websocket').client,
    client = new Client();

client.on('connect', function (sock) {
    messages = [
        'fooxx',
        'foo'
    ];

    console.error("connected!");
    sock.on('message', function (data) {
        console.log('got data', data);
        var msg;
        while ((msg = messages.shift())) {
            sock.send(msg);
        }
    });
    sock.on('close', function () {
        console.error('disconnected');
    });
});

client.connect('ws://localhost:8888/socket');
