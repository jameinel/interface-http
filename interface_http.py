import json

from ops.framework import EventBase, EventsBase, EventSource, Object, StoredState


class NewClientEvent(EventBase):
    """Emitted when a new unit joins a relation with the HTTP endpoint.

    :var client: The client that is connecting at this time.
    :type client: HTTPInterfaceClient
    """
    def __init__(self, handle, client):
        super().__init__(handle)
        self.client = client

    def snapshot(self):
        return {
            'relation_name': self.client._relation.name,
            'relation_id': self.client._relation.id,
        }

    def restore(self, snapshot):
        relation = self.model.get_relation(snapshot['relation_name'], snapshot['relation_id'])
        self.client = HTTPInterfaceClient(relation, self.model.unit)


class HTTPServerEvents(EventsBase):
    """These are the events that can be emitted by HTTPServer."""
    new_client = EventSource(NewClientEvent)


class HTTPServer(Object):
    """Represents the Provides side of an 'http' relation.

    Will emit() self.on.new_client when a unit joins a relation with this endpoint.
    The event emitted will be a NewClientEvent which has attribute .client
    describing who joined the relation.

    You can also look at .clients() to get the complete list of all connected clients.
    """

    on = HTTPServerEvents()
    _stored = StoredState()

    def __init__(self, charm, relation_name):
        """Initialize handling of the provides side of an 'http' interface.

        :param charm: the CharmBase using the http interface.
        :param relation_name: the name of the interface.
        """
        super().__init__(charm, relation_name)
        self._relation_name = relation_name
        self._stored.set_default('apps', [])
        self.framework.observe(charm.on[relation_name].relation_joined, self._on_joined)
        self.framework.observe(charm.on[relation_name].relation_departed, self._on_departed)

    @property
    def _relations(self):
        return self.model.relations[self._relation_name]

    def _on_joined(self, event):
        if event.app not in self._stored.apps:
            self.state.apps.append(event.app)
            self.on.new_client.emit(HTTPInterfaceClient(event.relation, self.model.unit))

    def _on_departed(self, event):
        self.state.apps = [app for app in self._relations]

    def clients(self):
        """Get the list of all clients of this HTTP server."""
        return [HTTPInterfaceClient(relation, self.model.unit) for relation in self._relations]


class HTTPInterfaceClient:
    """Identifies a remote unit that has joined a relation to this HTTP Server.

    This will be an attribute of NewClientEvent, which happens when someone joins the HTTP
    relation.
    """
    def __init__(self, relation, local_unit):
        self._relation = relation
        self._local_unit = local_unit
        self.ingress_address = relation.data[local_unit]['ingress-address']

    def serve(self, hosts, port):
        self._relation.data[self._local_unit]['extended_data'] = json.dumps([{
            'hostname': host,
            'port': port,
        } for host in hosts])

