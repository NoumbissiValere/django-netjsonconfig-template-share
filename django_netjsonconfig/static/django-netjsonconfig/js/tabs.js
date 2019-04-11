django.jQuery(function ($) {
  'use strict';
  if ($('.add-device').length) {
    return;
  }

  var showTab = function(menuLink){
    var tabId = menuLink.attr('href');
    $('ul.tabs a').removeClass('current');
    $('.tab-content').removeClass('current');
    menuLink.addClass('current');
    $(tabId).addClass('current');
    $.event.trigger({
      type: 'tabshown',
      tabId: tabId,
    });
    return tabId;
  },
  showFragment = function(fragment) {
    if (!fragment) { return; }
    showTab($('ul.tabs a[href="' + fragment + '"]'));
  };

  $('ul.tabs a').click(function(e){
    var tabId = showTab($(this));
    e.preventDefault();
    history.pushState(tabId, '', tabId);
  });

  var overview = $('#device_form > div > fieldset.module.aligned')
                     .addClass('tab-content')
                     .attr('id', 'overview-group'),
      tabs = $('#device_form > div > div.inline-group')
                 .addClass('tab-content'),
      tabsContainer = $('#tabs-container ul');
  tabs.each(function(i, el) {
    var $el = $(el),
        tabId = $el.attr('id'),
        label = $el.find('> fieldset.module > h2, ' +
                         '> .tabular > fieldset.module > h2').text();
    tabsContainer.append(
      '<li><a class="button" href="#' + tabId + '">' + label + '</a></li>'
    );
  });

  $('.tabs-loading').hide();

  // open fragment
  $(window).on('hashchange', function (e) {
    showFragment(window.location.hash);
  });

  $(window).on('load', function () {
    // open fragment on page opening if present
    if (window.location.hash) {
      showFragment(window.location.hash);
    } else {
      $('ul.tabs li:first-child a').addClass('current');
      overview.addClass('current');
    }
    $('#loading-overlay').fadeOut(400);
  });
});
