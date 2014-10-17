var Client = require('websocket').client,
    client = new Client();

client.on('connect', function (sock) {
    var login = ['foof', 'foo'],
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

client.on('connectFailed', function (err) {
    console.log('connect failed', err);
});

client.on('error', function (err) {
    console.log(err);
});

//client.connect('ws://localhost:8888/socket');
client.connect('ws://localhost:8060/socket');
