/**
 * Intercepts user credentials and stores in local storage. Credentials
 * are replayed when reconnected.
 */

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

            function ondata (data) {
                prompt = data.prompt || '';
            }

            function onsend (message) {
                console.log('message during login', message);

                if (prompt.match(/name$/i)) {
                    user.name = message;
                } else if (prompt.match(/quest$/i)) {
                    user.quest = message;
                } else {
                    sock.off('send', onsend);
                    sock.off('data', ondata);
                }

                if (isValidUser(user)) {
                    saveUserData(user);
                }
            }

            sock.on('send', onsend);
            sock.on('data', ondata);
        },

        resume: function (sock) {
            var user = loadUserData();
            if (!isValidUser(user)) {
                throw new Error('no existing user data');
            }

            function ondata(data) {
                var prompt = data.prompt || '';

                if (prompt.match(/name$/i)) {
                    sock.send(user.name);
                } else if (prompt.match(/quest$/i)) {
                    sock.send(user.quest);
                    console.log("Session resumed");
                    sock.off('data', ondata);
                }
            }

            sock.on('data', ondata);
        }
    };
});
