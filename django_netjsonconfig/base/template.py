import collections

from jsonfield import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from taggit.managers import TaggableManager

from ..settings import DEFAULT_AUTO_CERT
from .base import BaseConfig

TYPE_CHOICES = (
    ('generic', _('Generic')),
    ('vpn', _('VPN-client')),
)

FLAG_CHOICES = (
    ('private', _('Private')),
    ('public', _('Public')),
    ('shared_secret', _('Shared Secret'))
)


def default_auto_cert():
    """
    returns the default value for auto_cert field
    (this avoids to set the exact default value in the database migration)
    """
    return DEFAULT_AUTO_CERT


class AbstractTemplate(BaseConfig):
    """
    Abstract model implementing a
    netjsonconfig template
    """
    tags = TaggableManager(through='django_netjsonconfig.TaggedTemplate', blank=True,
                           help_text=_('A comma-separated list of template tags, may be used '
                                       'to ease auto configuration with specific settings (eg: '
                                       '4G, mesh, WDS, VPN, ecc.)'))
    vpn = models.ForeignKey('django_netjsonconfig.Vpn',
                            verbose_name=_('VPN'),
                            blank=True,
                            null=True,
                            on_delete=models.CASCADE)
    type = models.CharField(_('type'),
                            max_length=16,
                            choices=TYPE_CHOICES,
                            default='generic',
                            db_index=True,
                            help_text=_('template type, determines which '
                                        'features are available'))
    default = models.BooleanField(_('enabled by default'),
                                  default=False,
                                  db_index=True,
                                  help_text=_('whether new configurations will have '
                                              'this template enabled by default'))
    auto_cert = models.BooleanField(_('auto certificate'),
                                    default=default_auto_cert,
                                    db_index=True,
                                    help_text=_('whether x509 client certificates should '
                                                'be automatically managed behind the scenes '
                                                'for each configuration using this template, '
                                                'valid only for the VPN type'))
    flag = models.CharField(_('Flag'),
                            choices=FLAG_CHOICES,
                            max_length=16,
                            default='private',
                            help_text=_('Please choose if this template should be '
                                        'Public, Private or shared secretly'))

    variable = JSONField(_('context'),
                         null=True,
                         blank=True,
                         help_text=_('Provide values for the list of variables found at the '
                                     'detail page of this template at the Library'),
                         load_kwargs={'object_pair_hook': collections.OrderedDict},
                         dump_kwargs={'indent': 4})

    __template__ = True

    class Meta:
        abstract = True
        verbose_name = _('template')
        verbose_name_plural = _('templates')

    def save(self, *args, **kwargs):
        """
        modifies status of related configs
        if key attributes have changed (queries the database)
        """
        update_related_config_status = False
        if not self._state.adding:
            current = self.__class__.objects.get(pk=self.pk)
            for attr in ['backend', 'config']:
                if getattr(self, attr) != getattr(current, attr):
                    update_related_config_status = True
                    break
        # save current changes
        super(AbstractTemplate, self).save(*args, **kwargs)
        # update relations
        if update_related_config_status:
            self._update_related_config_status()

    def _update_related_config_status(self):
        self.config_relations.update(status='modified')
        for config in self.config_relations.all():
            config._send_config_modified_signal()

    def clean(self, *args, **kwargs):
        """
        * ensures VPN is selected if type is VPN
        * clears VPN specific fields if type is not VPN
        * automatically determines configuration if necessary
        """
        super(AbstractTemplate, self).clean(*args, **kwargs)
        if self.type == 'vpn' and not self.vpn:
            raise ValidationError({
                'vpn': _('A VPN must be selected when template type is "VPN"')
            })
        elif self.type != 'vpn':
            self.vpn = None
            self.auto_cert = False
        if self.type == 'vpn' and not self.config:
            self.config = self.vpn.auto_client(auto_cert=self.auto_cert)


AbstractTemplate._meta.get_field('config').blank = True
