import re

from ..plugin import CommandPlugin
import nocworx

class NocworxPlugin(CommandPlugin):
    REPLY_SERVER_LOOKUP = '{ip} should have {cpu_used}x{cpu_desc}, {ram_desc} ' \
        'RAM, and {drives}'

    @CommandPlugin.config_types(hosturl=str, username=str, password=str)
    def __init__(self, core, hosturl, username, password):
        super(NocworxPlugin, self).__init__(core)
        self._api = nocworx.NocworxApi(hosturl, username, password)

    @CommandPlugin.register_command(r'nocloc\s+(.+)')
    def look_up_location(self, chans, name, match, direct, reply):
        hostname = match.groups(1)
        location = self._api.host.get(hostname=hostname)
        reply('Host should be at {location}'.format(location=location))

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
                            ip=ip, drives=self._get_drive_count(s[0]), **s[0]))
                        return
            else:
                reply('No matches found :(')
        except nocworx.ApiException as e:
            reply('API Error: {0}'.format(e))

    def _get_drive_count(self, server):
        types = list(set(v for (k, v) in server.iteritems() \
            if k.startswith('hdd') and k.endswith('_desc') and not v.startswith('0')))
        drive_count = dict((k, len([v for v in server.itervalues() if v == k])) \
            for k in types)
        return ', '.join('{c}x{d}'.format(c=c, d=d) for (d, c) in drive_count.iteritems())
