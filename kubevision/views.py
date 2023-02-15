import json
import logging

from tornado import web

from kubevision.common import conf
from kubevision.common import context
from kubevision.k8s import api

from kubevision.common import constants
from kubevision.common import utils

LOG = logging.getLogger(__name__)
CONF = conf.CONF

CONF_DB_API = None
RUN_AS_CONTAINER = False
ROUTES = []


def registry_route(url):

    def registry(cls):
        global ROUTES

        ROUTES.append((url, cls))
        return cls
    return registry


class BaseReqHandler(web.RequestHandler):

    def _get_context(self):
        return context.ClusterContext(self.get_cookie('clusterId'),
                                      region=self.get_cookie('region'))

    def return_resp(self, status, data):
        self.set_status(status)
        self.finish(data)


@registry_route(r'/')
class Index(web.RequestHandler):

    def get(self):
        self.redirect('/dashboard')


@registry_route(r'/dashboard')
class Dashboard(BaseReqHandler):

    def get(self):
        self.render('dashboard.html', name=constants.NAME, cluster='')


@registry_route(r'/node')
class Node(BaseReqHandler):

    @utils.response
    def get(self):
        items = api.CLIENT.list_node()
        return {'nodes': [item.__dict__ for item in items]}


@registry_route(r'/namespace')
class Namespace(BaseReqHandler):

    @utils.response
    def get(self):
        namespaces = api.CLIENT.list_namespace()
        return {'namespaces': [item.__dict__ for item in namespaces]}


@registry_route(r'/deployment')
class Deployment(BaseReqHandler):

    @utils.response
    def get(self):
        items = api.CLIENT.list_deploy()
        return {'deployments': [item.__dict__ for item in items]}


@registry_route(r'/daemonset')
class Daemonset(BaseReqHandler):

    @utils.response
    def get(self):
        items = api.CLIENT.list_daemonset()
        return {'daemonsets': [item.__dict__ for item in items]}


@registry_route(r'/pod')
class Pod(BaseReqHandler):

    @utils.response
    def get(self):
        items = api.CLIENT.list_pod()
        return {'pods': [item.__dict__ for item in items]}


class Configs(web.RequestHandler):

    def get(self):
        global CONF_DB_API

        self.set_status(200)
        self.finish({'configs': [
            item.to_dict() for item in CONF_DB_API.list()]
        })


class Cluster(web.RequestHandler):

    def get(self):
        cluster_list = api.query_cluster()
        self.set_status(200)
        self.finish({
            'clusters': [cluster.to_dict() for cluster in cluster_list]
        })

    def post(self):
        data = json.loads(self.request.body)
        cluster = data.get('cluster', {})
        LOG.debug('add cluster: %s', data)
        try:
            api.create_cluster(cluster.get('name'), cluster.get('authUrl'),
                               cluster.get('authProject'),
                               cluster.get('authUser'),
                               cluster.get('authPassword'))
            self.set_status(200)
            self.finish(json.dumps({}))
        except Exception as e:
            LOG.exception(e)
            self.set_status(400)
            self.finish({'error': str(e)})

    def delete(self, cluster_id):
        deleted = api.delete_cluster_by_id(cluster_id)
        if deleted >= 1:
            self.set_status(204)
            self.finish()
        else:
            self.set_status(404)
            self.finish({'error': f'cluster {cluster_id} is not found'})
        return


def get_routes():
    return ROUTES
