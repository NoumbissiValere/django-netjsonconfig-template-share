from collections import OrderedDict
import json, urllib.request
from jsonfield import JSONField

from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from taggit.managers import TaggableManager

from ..settings import DEFAULT_AUTO_CERT
from .base import BaseConfig
from ..utils import get_random_key
from ..validators import key_validator

TYPE_CHOICES = (
    ('generic', _('Generic')),
    ('vpn', _('VPN-client')),
)

FLAG_CHOICES = (
    ('private', _('Private')),
    ('public', _('Public')),
    ('shared_secret', _('Shared Secret')),
     ('import', _('Import'))
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
                            default='private',
                            max_length=16,
                            db_index=True,
                            help_text=_('Whether to keep this template private or make it '
                                        'public, shared secretly or imported'))
    key = models.CharField(max_length=64,
                           unique=True,
                           db_index=True,
                           default=get_random_key,
                           validators=[key_validator],
                           help_text=_('share template key'))
    description = models.TextField(_('Description'),
                                   blank=True,
                                   null=True,
                                   help_text=_('Enter public description of this template'))
    notes = models.TextField(_('Notes'),
                             blank=True,
                             null=True,
                             help_text=_('Enter internal notes for the administrators'))
    variable = JSONField(_('Variable'),
                         default=dict,
                         blank=True,
                         help_text=_('Enter Values for the variables used by this template'),
                         load_kwargs={'object_pairs_hook': OrderedDict},
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
        if self.flag == 'public' or self.flag == 'shared_secret':
            if not self.description:
                raise ValidationError({'description': _('Please enter public description of '
                                                        'shared template')})
            if not self.notes:
                raise ValidationError({'notes': _('Please enter notes used by administrations of '
                                                  'shared template')})
            if self.variable == {}:
                raise ValidationError({'variable': _('Please enter default values for variables ')})
        if self.flag == 'import':
            if self.url is None:
                raise ValidationError({'url': _('Please enter the Url to import template from')})
            else:
                try:
                    with urllib.request.urlopen(self.url) as response:
                        try:
                            data = json.loads(response.read().decode())
                            self.id = data['id']
                            self.type = data['type']
                            self.config = json.dumps(eval(data['config']))
                            self.url = data['url']
                            self.variable = json.dumps(eval(data['variable']))
                            self.vpn = data['vpn']
                            self.auto_cert = data['auto_cert']
                            self.backend = data['backend']
                            #self.key = data['key']
                        except ValueError:
                            raise ValidationError({'url', _('Url is not valid')})
                except urllib.request.HTTPError:
                    raise ValidationError({'url': _('Url is not valid. Please check it')})


AbstractTemplate._meta.get_field('config').blank = True
