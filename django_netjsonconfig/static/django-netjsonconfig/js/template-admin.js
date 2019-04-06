django.jQuery(function ($) {
    'use strict';
    var operationType = $('.field-operation_type select');
    $('.jsoneditor-wrapper').hide()
    // enable switcher only in add forms
    if (!operationType.length || $('form .deletelink-box').length > 0) {
        $('.field-operation_type').hide();
        $('.field-url').hide();
        return;
    }
    // function for operation_type switcher
    var showFields = function () {
        // define fields for each operation
        var importFields = $('.form-row:not(.field-url, .field-operation_type, ' +
                          '.field-variable, .field-default, .field-created, .field-modified)'),
            newFields = $('.form-row:not(.field-url, .field-variable, .field-config)'),
            defaultFields = $('.form-row:not(.field-operation_type)'),
            allFields = $('.form-row'),
            value = operationType.val();
        if (value === '-') {
            allFields.show();
            defaultFields.hide();
        }
        if (value === 'new') {
            allFields.hide();
            newFields.show();
        }
        if (value === 'import') {
            allFields.show();
            importFields.hide();
        }
        if (value === '-' || value === 'import'){
            $('.jsoneditor-wrapper').hide();
        }
        else{
            $('.jsoneditor-wrapper').show();
        }
    };
    showFields();
    operationType.on('change', function (e) {
        showFields();
    });
});
