from __future__ import print_function, absolute_import
from novaagent import utils
from novaagent.common.password import PasswordCommands
from subprocess import Popen, PIPE

from novaagent.libs import DefaultOS


class ServerOS(DefaultOS):
    def _setup_interface(self, ifname, iface):
        with open('/etc/sysconfig/network-scripts/ifcfg-{0}'.format(ifname), 'w') as iffile:
            print('# Label {0}'.format(iface['label']), file=iffile)
            print('BOOTPROTO=static', file=iffile)
            print('DEVICE={0}'.format(ifname), file=iffile)
            count = 0
            for x in iface['ips']:
                if count == 0:
                    print('IPADDR={0}'.format(x['ip']), file=iffile)
                    print('NETMASK={0}'.format(x['netmask']), file=iffile)
                else:
                    print('IPADDR{0}={1}'.format(count, x['ip']), file=iffile)
                    print('NETMASK{0}={1}'.format(count, x['netmask']), file=iffile)
                count += 1
            if 'gateway' in iface and iface['gateway']:
                print('GATEWAY={0}'.format(iface['gateway']), file=iffile)
            if 'ip6s' in iface and iface['ip6s']:
                print('IPV6INIT=yes', file=iffile)
                count = 0
                for x in iface['ip6s']:
                    if count == 0:
                        print('IPV6ADDR={ip}/{netmask}'.format(**x), file=iffile)
                    else:
                        print('IPV6ADDR{0}={ip}/{netmask}'.format(count, **x), file=iffile)
                    count += 1
                print('IPV6_DEFAULTGW={0}%{1}'.format(iface['gateway_v6'], ifname), file=iffile)
            if 'dns' in iface and iface['dns']:
                count = 1
                for dns in iface['dns']:
                    print("DNS{0}={1}".format(count, dns), file=iffile)
                    count += 1
            print('ONBOOT=yes', file=iffile)
            print('NM_CONTROLLED=no', file=iffile)
        if 'routes' in iface and iface['routes']:
            routes = ['{route}/{netmask} via {gateway}'.format(**x) for x in iface['routes']]
            print("Routes=('{0}')".format("' '".join(routes)), file=iffile)

    def resetnetwork(self, name, value):
        ifaces = {}
        xen_macs = utils.list_xenstore_macaddrs()
        for iface in utils.list_hw_interfaces():
            mac = utils.get_hw_addr(iface)
            if not mac or mac not in xen_macs:
                continue
            ifaces[iface] = utils.get_interface(mac)

        # set hostname
        hostname = utils.get_hostname()
        if os.path.exists('/usr/bin/hostnamectl'):
            p = Popen(['hostnamectl', 'set-hostname', hostname], stdout=PIPE, stderr=PIPE, stdin=PIPE)
            out, err = p.communicate()
            if p.returncode != 0:
                return (str(p.returncode), 'Error setting hostname')
        else:
            with open('/etc/sysconfig/network') as netfile:
                print('NETWORKING=yes', file=netfile)
                print('NOZEROCONF=yes', file=netfile)
                print('NETWORKING_IPV6=yes', file=netfile)
                print('HOSTNAME={0}'.format(hostname), file=netfile)
            p = Popen(['hostname', hostname], stdout=PIPE, stderr=PIPE, stdin=PIPE)
            out, err = p.communicate()
            if p.returncode != 0:
                return (str(p.returncode), 'Error setting hostname')

        # setup interface files
        for ifname, iface in ifaces.items():
            self._setup_interface(ifname, iface)
        p = Popen(['service', 'network', 'restart'], stdout=PIPE, stderr=PIPE, stdin=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            return (str(p.returncode), 'Error restarting network')

        return ('0', '')


if __name__ == '__main__':
    main()