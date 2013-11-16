define(['jquery'], function ($) {
    'use strict';

    var $status = $('#status');

    return function setStatus (status, message) {
        console.log('status changed', status);
        $status.attr('data-status', status);
        $status.find('span.message').text(message || status);
    };
});
