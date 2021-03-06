import subprocess

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from .. import settings as app_settings
from .base import BaseConfig


class AbstractVpn(BaseConfig):
    """
    Abstract VPN model
    """
    host = models.CharField(max_length=64, help_text=_('VPN server hostname or ip address'))
    ca = models.ForeignKey('django_x509.Ca', verbose_name=_('CA'), on_delete=models.CASCADE)
    cert = models.ForeignKey('django_x509.Cert',
                             verbose_name=_('x509 Certificate'),
                             help_text=_('leave blank to create automatically'),
                             blank=True,
                             null=True,
                             on_delete=models.CASCADE)
    backend = models.CharField(_('VPN backend'),
                               choices=app_settings.VPN_BACKENDS,
                               max_length=128,
                               help_text=_('Select VPN configuration backend'))
    notes = models.TextField(blank=True)
    # diffie hellman parameters are required
    # in some VPN solutions (eg: OpenVPN)
    dh = models.TextField(blank=True)

    __vpn__ = True

    class Meta:
        verbose_name = _('VPN server')
        verbose_name_plural = _('VPN servers')
        abstract = True

    def clean(self, *args, **kwargs):
        """
        * ensure certificate matches CA
        """
        super(AbstractVpn, self).clean(*args, **kwargs)
        # certificate must be related to CA
        if self.cert and self.cert.ca.pk != self.ca.pk:
            msg = _('The selected certificate must match the selected CA.')
            raise ValidationError({'cert': msg})

    def save(self, *args, **kwargs):
        """
        Calls _auto_create_cert() if cert is not set
        """
        if not self.cert:
            self.cert = self._auto_create_cert()
        if not self.dh:
            self.dh = self.dhparam(1024)
        super(AbstractVpn, self).save(*args, **kwargs)

    @classmethod
    def dhparam(cls, length):
        """
        Returns an automatically generated set of DH parameters in PEM
        """
        return subprocess.check_output('openssl dhparam {0} 2> /dev/null'.format(length),
                                       shell=True)

    def _auto_create_cert(self):
        """
        Automatically generates server x509 certificate
        """
        common_name = slugify(self.name)
        server_extensions = [
            {
                "name": "nsCertType",
                "value": "server",
                "critical": False
            }
        ]
        cert_model = self.__class__.cert.field.related_model
        cert = cert_model(name=self.name,
                          ca=self.ca,
                          key_length=self.ca.key_length,
                          digest=self.ca.digest,
                          country_code=self.ca.country_code,
                          state=self.ca.state,
                          city=self.ca.city,
                          organization_name=self.ca.organization_name,
                          email=self.ca.email,
                          common_name=common_name,
                          extensions=server_extensions)
        cert = self._auto_create_cert_extra(cert)
        cert.save()
        return cert

    def _auto_create_cert_extra(self, cert):
        """
        this method can be overridden in order to perform
        extra operations on a Cert object when auto-creating
        certificates for VPN servers
        """
        return cert

    def get_context(self):
        """
        prepares context for netjsonconfig VPN backend
        """
        try:
            c = {'ca': self.ca.certificate}
        except ObjectDoesNotExist:
            c = {}
        if self.cert:
            c.update({
                'cert': self.cert.certificate,
                'key': self.cert.private_key
            })
        if self.dh:
            c.update({'dh': self.dh})
        return c

    def _get_auto_context_keys(self):
        """
        returns a dictionary which indicates the names of
        the configuration variables needed to access:
            * path to CA file
            * CA certificate in PEM format
            * path to cert file
            * cert in PEM format
            * path to key file
            * key in PEM format
        """
        pk = self.pk.hex
        return {
            'ca_path': 'ca_path_{0}'.format(pk),
            'ca_contents': 'ca_contents_{0}'.format(pk),
            'cert_path': 'cert_path_{0}'.format(pk),
            'cert_contents': 'cert_contents_{0}'.format(pk),
            'key_path': 'key_path_{0}'.format(pk),
            'key_contents': 'key_contents_{0}'.format(pk),
        }

    def auto_client(self, auto_cert=True):
        """
        calls backend ``auto_client`` method and returns a configuration
        dictionary that is suitable to be used as a template
        if ``auto_cert`` is ``False`` the resulting configuration
        won't include autogenerated key and certificate details
        """
        config = {}
        backend = self.backend_class
        if hasattr(backend, 'auto_client'):
            context_keys = self._get_auto_context_keys()
            # add curly brackets for netjsonconfig context evaluation
            for key in context_keys.keys():
                context_keys[key] = '{{%s}}' % context_keys[key]
            # do not include cert and key if auto_cert is False
            if not auto_cert:
                for key in ['cert_path', 'cert_contents', 'key_path', 'key_contents']:
                    del context_keys[key]
            conifg_dict_key = self.backend_class.__name__.lower()
            auto = backend.auto_client(host=self.host,
                                       server=self.config[conifg_dict_key][0],
                                       **context_keys)
            config.update(auto)
        return config


class AbstractVpnClient(models.Model):
    """
    m2m through model
    """
    config = models.ForeignKey('django_netjsonconfig.Config',
                               on_delete=models.CASCADE)
    vpn = models.ForeignKey('django_netjsonconfig.Vpn',
                            on_delete=models.CASCADE)
    cert = models.OneToOneField('django_x509.Cert',
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)
    # this flags indicates whether the certificate must be
    # automatically managed, which is going to be almost in all cases
    auto_cert = models.BooleanField(default=False)

    class Meta:
        abstract = True
        unique_together = ('config', 'vpn')
        verbose_name = _('VPN client')
        verbose_name_plural = _('VPN clients')

    def save(self, *args, **kwargs):
        """
        automatically creates an x509 certificate when ``auto_cert`` is True
        """
        if self.auto_cert:
            cn = self._get_common_name()
            self._auto_create_cert(name=self.config.device.name,
                                   common_name=cn)
        super(AbstractVpnClient, self).save(*args, **kwargs)

    def _get_common_name(self):
        """
        returns the common name for a new certificate
        """
        d = self.config.device
        cn_format = app_settings.COMMON_NAME_FORMAT
        if cn_format == '{mac_address}-{name}' and d.name == d.mac_address:
            cn_format = '{mac_address}'
        return cn_format.format(**d.__dict__)

    @classmethod
    def post_delete(cls, **kwargs):
        """
        class method for ``post_delete`` signal
        automatically deletes certificates when ``auto_cert`` is ``True``
        """
        instance = kwargs['instance']
        if instance.auto_cert:
            instance.cert.delete()

    def _auto_create_cert(self, name, common_name):
        """
        Automatically creates and assigns a client x509 certificate
        """
        server_extensions = [
            {
                "name": "nsCertType",
                "value": "client",
                "critical": False
            }
        ]
        ca = self.vpn.ca
        cert_model = self.__class__.cert.field.related_model
        cert = cert_model(name=name,
                          ca=ca,
                          key_length=ca.key_length,
                          digest=str(ca.digest),
                          country_code=ca.country_code,
                          state=ca.state,
                          city=ca.city,
                          organization_name=ca.organization_name,
                          email=ca.email,
                          common_name=common_name,
                          extensions=server_extensions)
        cert = self._auto_create_cert_extra(cert)
        cert.full_clean()
        cert.save()
        self.cert = cert
        return cert

    def _auto_create_cert_extra(self, cert):
        """
        this method can be overridden in order to perform
        extra operations on a Cert object when auto-creating
        certificates for VPN clients
        """
        return cert
