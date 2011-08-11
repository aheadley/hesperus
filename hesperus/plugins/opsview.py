import opsview
import ..plugin
import time

class OpsviewPlugin(CommandPlugin,PollPlugin):
    @plugin.Plugin.config_types(url=str, username=str, password=str, max_state_duration=int)
    def __init__(self, core, url=None, username=None, password=None, max_state_duration=43200):
        super(OpsviewPlugin, self).__init__(core)
        if any(map(lambda x: x is None, [url, username, password])):
            raise Exception('Missing setting')
        else:
            self.opsview_server = opsview.OpsviewServer(
                base_url=url,
                username=username,
                password=password)
            self.max_state_duration = max_state_duration
            self.alerting = []

    @plugin.CommandPlugin.register_command(r'status')
    def status_command(self, chans, match, direct, reply):
        pass

    @plugin.CommandPlugin.register_command(r'ack\s+([0-9A-Za-z\._-]+)(?: ())')
    def ack_command(self, chans, match, direct, reply):
        pass

    @plugin.CommandPlugin.register_command(r'ackall\s+(.+)')
    def ack_command(self, chans, match, direct, reply):
        pass

    poll_interval = 15.0
    def poll(self):
        pass
