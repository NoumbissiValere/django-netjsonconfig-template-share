django.jQuery(function ($) {
    'use strict';
    var flag = $('.field-flag select');
    $('.jsoneditor-wrapper').hide()

    // function for flag_type switcher
    var showFields = function () {
        // define fields for each operation
        var importFields = $('.form-row:not(.field-name, .field-type, .field-backend, .field-vpn, '+
                          '.field-auto_cert, .field-tags, .field-config, .field-description, '+
                          '.field-notes, .field-key, .field-variable)'),
            publicFields = $('.form-row:not(.field-url, .field-config, .field-key)'),
            shareFields = $('.form-row:not(.field-url, .field-config)'),
            privateFields = $('.form-row:not(.field-url, .field-variable, .field-description, '+
                                            '.field-notes, .field-config, .field-key)'),
            allFields = $('.form-row'),
            value = flag.val();
        if (value === 'private') {
            allFields.hide();
            privateFields.show();
        }
        if (value === 'public') {
            allFields.hide();
            publicFields.show();
        }
        if (value === 'shared_secret'){
            allFields.hide();
            shareFields.show();
        }
        if (value === 'import') {
            allFields.hide();
            importFields.show();
        }
        if (value === 'import'){
            $('.jsoneditor-wrapper').hide();
        }
        else{
            $('.jsoneditor-wrapper').show();
        }
    };
    showFields();
    flag.on('change', function (e) {
        showFields();
    });
});
