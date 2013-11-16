define(function () {
    function loadUserData () {
        var data = window.localStorage['user'],
            user;

        if (data) {
            try {
                user = JSON.parse(data);
            } catch (err) {
                console.log(err);
            }
        }
        console.log('user information', user);
        return user;
    }

    function saveUserData (user) {
        console.log('saving user information', user);
        window.localStorage['user'] = JSON.stringify(user);
    }

    function isValidUser (user) {
        return user && user.name && user.quest;
    }

    return {
        forget: function () {
            saveUserData({});
        },

        watch: function (sock) {
            var prompt = '',
                user = {};

            function onrecv (data) {
                prompt = data.prompt || '';
            }

            function onsend (message) {
                console.log('message during login', message);

                if (prompt.match(/name$/)) {
                    user.name = message;
                } else if (prompt.match(/quest$/)) {
                    user.quest = message;
                } else {
                    sock.off('send', onsend);
                    sock.off('recv', onrecv);
                }

                if (isValidUser(user)) {
                    saveUserData(user);
                }
            }

            sock.on('send', onsend);
            sock.on('recv', onrecv);
        },

        resume: function (sock) {
            var user = loadUserData();
            if (!isValidUser(user)) {
                throw new Error('no existing user data');
            }

            function onrecv(data) {
                var prompt = data.prompt || '';

                if (prompt.match(/name$/)) {
                    sock.send(user.name);
                } else if (prompt.match(/quest$/)) {
                    sock.send(user.quest);
                } else if (data.message.match(/welcome/i)) {
                    sock.off('recv', onrecv);
                }
            }

            sock.on('recv', onrecv);
        }
    };
});
