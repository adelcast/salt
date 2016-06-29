# -*- coding: utf-8 -*-
'''
 Beacon to annouce via avahi (zeroconf)

'''
# Import Python libs
from __future__ import absolute_import
import logging

# Import 3rd Party libs
try:
    import avahi
    HAS_PYAVAHI = True
except ImportError:
    HAS_PYAVAHI = False
import dbus

log = logging.getLogger(__name__)

__virtualname__ = 'avahi_announce'

_INITIALIZED_ = False
BUS = dbus.SystemBus()
SERVER = dbus.Interface(BUS.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER),
                        avahi.DBUS_INTERFACE_SERVER)
GROUP = dbus.Interface(BUS.get_object(avahi.DBUS_NAME, SERVER.EntryGroupNew()),
                       avahi.DBUS_INTERFACE_ENTRY_GROUP)


def __virtual__():
    if HAS_PYAVAHI:
        return __virtualname__
    return False


def validate(config):
    '''
    Validate the beacon configuration
    '''
    if not isinstance(config, dict):
        return False, ('Configuration for avahi_announcement '
                       'beacon must be a dictionary')
    elif not all(x in list(config.keys()) for x in ('servicetype', 'port', 'txt')):
        return False, ('Configuration for avahi_announce beacon '
                       'must contain servicetype, port and txt items')
    return True, 'Valid beacon configuration'


def beacon(config):
    '''
    Briadcast values via zeronconf

    It's adviced to set the interval to -1 (do not emmit) since the beacon, once
    initialized won't change it's configuration. Grains can be used to define
    txt values using the syntax: grains.<grain_name>

    The default sercicename its the hostname grain value.

    Example Config

    .. code-block:: taml

       beacons:
          avahi_announce:
             interval: -1
             servicetype: _demo._tcp
             txt:
                ProdName: grains.productname
                SerialNo: grains.serialnumber
                Comments: 'this is a test'
    '''
    ret = []

    global _INITIALIZED_

    if not _INITIALIZED_:
        changes = {}
        txt = {}

        _INITIALIZED_ = True

        _validate = validate(config)
        if not _validate[0]:
            log.warning('Beacon {0} configuration invalid, '
                        'not adding. {1}'.format(__virtualname__, _validate[1]))
            return ret

        if 'servicename' in config:
            servicename = config['servicename']
        else:
            servicename = __grains__['host']

        for item in config['txt']:
            if config['txt'][item].startswith('grains.'):
                txt[item] = __grains__[config['txt'][item][7:]]
            else:
                txt[item] = config['txt'][item]
            changes[str('txt.' + item)] = txt[item]

        # Need to update the announcement
        GROUP.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0),
                         servicename, config['servicetype'], '', '',
                         dbus.UInt16(config['port']), avahi.dict_to_txt_array(txt))
        GROUP.Commit()

        changes['servicename'] = servicename
        changes['servicetype'] = config['servicetype']
        changes['port'] = config['port']

        ret.append({'tag': 'result', 'changes': changes})

    return ret
