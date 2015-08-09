#!/usr/bin/python

# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# The hooks of this charm have been symlinked to functions
# in this file.

import sys

from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    log,
    relation_set,
    relation_ids,
    config,
)

from charmhelpers.fetch import (
    apt_install,
    apt_purge,
    configure_sources,
)

from pg_edge_utils import (
    register_configs,
    ensure_files,
    restart_pg,
    stop_pg,
    determine_packages,
    load_iovisor,
    remove_iovisor,
    ensure_mtu,
    add_lcm_key,
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    '''
    Install hook is run when the charm is first deployed on a node.
    '''
    configure_sources(update=True)
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, options=['--force-yes'], fatal=True)
    load_iovisor()
    ensure_mtu()
    ensure_files()
    add_lcm_key()


@hooks.hook('plumgrid-relation-joined')
def plumgrid_joined():
    '''
    This hook is run when relation between plumgrid-edge and
    plumgrid-director is made.
    '''
    ensure_mtu()
    ensure_files()
    add_lcm_key()
    CONFIGS.write_all()
    restart_pg()


@hooks.hook('neutron-plugin-relation-joined')
@hooks.hook('plumgrid-plugin-relation-joined')
def neutron_plugin_joined(relation_id=None):
    rel_data = {
        'metadata-shared-secret': config('metadata-shared-key'),
    }
    relation_set(relation_id=relation_id, **rel_data)


@hooks.hook('config-changed')
def config_changed():
    '''
    This hook is run when a config parameter is changed.
    It also runs on node reboot.
    '''
    stop_pg()
    configure_sources(update=True)
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, options=['--force-yes'], fatal=True)
    load_iovisor()
    ensure_mtu()
    for rid in relation_ids('neutron-plugin'):
        neutron_plugin_joined(rid)
    for rid in relation_ids('plumgrid-plugin'):
        neutron_plugin_joined(rid)
    ensure_files()
    add_lcm_key()
    CONFIGS.write_all()
    restart_pg()


@hooks.hook('stop')
def stop():
    '''
    This hook is run when the charm is destroyed.
    '''
    stop_pg()
    remove_iovisor()
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_purge(pkg, fatal=False)


def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
