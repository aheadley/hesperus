import re
import socket

from ..plugin import CommandPlugin
import nocworx

class NocworxPlugin(CommandPlugin):
    REPLY_SERVER_LOOKUP = '{ip} ({service_desc}) should have {cpu_used}x{cpu_desc}, {ram_desc} ' \
        'RAM, and {drives}'
    REPLY_SERVER_LOCATION = '{ip} ({alloc[main_ip]}) is at {alloc[location]} / ' \
        '{alloc[network-switches][0][hostname]}#{alloc[network-switches][0][ports][0][name]} / ' \
        '{alloc[power-switches][0][hostname]}#{alloc[power-switches][0][ports][0][name]}'

    @CommandPlugin.config_types(hosturl=str, username=str, password=str)
    def __init__(self, core, hosturl, username, password):
        super(NocworxPlugin, self).__init__(core)
        self._api = nocworx.NocworxApi(hosturl, username, password)

    @CommandPlugin.register_command(r'nocloc\s+(.+)')
    def look_up_location(self, chans, name, match, direct, reply):
        try:
            ip = socket.gethostbyname(match.group(1))
        except socket.gaierror:
            reply('I dunno what that is')
            return
        self.log_debug('{0} -> {1}'.format(match.group(1), ip))
        allocs = self._api.allocation_dedicated.list(search=ip)
        for alloc in allocs:
            self.log_debug(alloc)
            if ip in alloc['ip_addresses']:
                reply(self.REPLY_SERVER_LOCATION.format(ip=ip, alloc=alloc))
                break

    @CommandPlugin.register_command(r'nocsrv\s+(.+)')
    def look_up_server(self, chans, name, match, direct, reply):
        m = match.groups(1)[0].strip()
        if re.match(r'(?:\d{1,3}\.){3}\d{1,3}', m):
            ip = m
        else:
            reply('"{m}" doesn\'t look like an IP address to me...'.format(m=m))
            return
        try:
            for service in self._api.client_service.list(search=ip):
                self.log_debug(service)
                allocation = self._api.client_service_hosting.list_allocations(
                    service_id=service['service_id'])
                self.log_debug(allocation)
                for server in self._api.allocation_dedicated.list_servers(
                        allocation_id=allocation['allocation_id']):
                    self.log_debug(server)
                    s = self._api.server.list(search='id:{server_id}'.format(**server))
                    if s:
                        reply(self.REPLY_SERVER_LOOKUP.format(
                            ip=ip, service_desc=service['description'],
                            drives=self._get_drive_count(s[0]), **s[0]))
                        return
            else:
                reply('No matches found :(')
        except nocworx.ApiException as e:
            reply('API Error: {0}: {1}'.format(e.__class__.__name__, e))

    def _get_drive_count(self, server):
        types = list(set(v for (k, v) in server.iteritems() \
            if k.startswith('hdd') and k.endswith('_desc') and not v.startswith('0')))
        drive_count = dict((k, len([v for v in server.itervalues() if v == k])) \
            for k in types)
        return ', '.join('{c}x{d}'.format(c=c, d=d) for (d, c) in drive_count.iteritems())
