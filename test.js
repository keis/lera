var Client = require('websocket').client,
    client = new Client();

client.on('connect', function (sock) {
    var login = ['fooy', 'foo'],
        messages = ['go south'];
//, 'go south'];

    console.error("connected!");
    sock.on('message', function (data) {
        console.log('got data', data);
        var msg;

        if (login.length) {
            while ((msg = login.shift())) {
                console.log('sending', msg);
                sock.send(msg);
            }
            return;
        }

        if (messages.length) {
            setTimeout(function () {
                while ((msg = messages.shift())) {
                    console.log('sending', msg);
                    sock.send(msg);
                }
            }, 100);
        }
    });
    sock.on('close', function () {
        console.error('disconnected');
    });
});

client.connect('ws://localhost:8888/socket');
