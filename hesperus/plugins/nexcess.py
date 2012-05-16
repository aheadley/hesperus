from .command import CommandPlugin
from ..plugin import PollPlugin
from opsview.api import RestApi

class OpsviewRestPlugin(CommandPlugin, PollPlugin):
    poll_interval = 15
    @CommandPlugin.config_types(base_url=str, username=str, password=str)
    def __init__(self, core, base_url, username, password):
        super(OpsviewRestPlugin, self).__init__(core)
        self._api = RestApi(base_url)
        self._api.authenticate(username, password)

    def poll(self):
        new_alerts = []
        services = self._api.services.get() #options to select alerting services
        hosts = self._api.hosts.get() #same
        for host in (h for h in hosts if h['acknowledged'] != 'yes'):

class NocworxPlugin(CommandPlugin):
    @CommandPlugin.config_types(host=str, api_key=str)
    def __init__(self, core, host, api_key):
        super(NocworxPlugin, self).__init__(core)
        self._api = NocworxApi(host, api_key)

    @CommandPlugin.register_command(r'nocloc\s+(.+)')
    def look_up_location(self, chans, name, match, direct, reply):
        hostname = match.groups(1)
        location = self._api.host.get(hostname=hostname)
        reply('Host should be at {location}'.format(location=location))
