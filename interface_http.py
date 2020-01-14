import json

from ops.framework import EventBase, EventsBase, EventSource, Object


class NewClient(EventBase):
    pass


class HTTPServerEvents(EventsBase):
    new_client = EventSource(NewClient)


class HTTPServer(Object):
    on = HTTPServerEvents()

    def __init__(self, parent, relation_name):
        super().__init__(parent, relation_name)
        self.relation_name = relation_name
        self.framework.observe(parent.on[relation_name].relation_joined, self.new_unit)

    @property
    def _relations(self):
        return self.model.relations[self.relation_name]

    def new_unit(self, event):
        self.on.new_client.emit()

    def clients(self):
        return [HTTPInterfaceClient(relation, self.model.unit) for relation in self._relations]


class HTTPInterfaceClient:
    def __init__(self, relation, unit):
        self._relation = relation
        self._unit = unit
        self.ingress_address = relation.data[unit]['ingress-address']

    def serve(self, hosts, port):
        self._relation.data[self._unit]['extended_data'] = json.dumps([{
            'hostname': host,
            'port': port,
        } for host in hosts])
