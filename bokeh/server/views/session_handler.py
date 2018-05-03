''' Abstract request handler that handles bokeh-session-id

'''
from __future__ import absolute_import, print_function

import logging

log = logging.getLogger(__name__)

from tornado import gen
from tornado.web import HTTPError, RequestHandler

from bokeh.util.session_id import generate_session_id, check_session_id_signature
from bokeh.server.views.sessions import TornadoSessionHandler, setup_session, save_session


class SessionHandler(RequestHandler):
    ''' Implements a custom Tornado handler for document display page

    '''
    def __init__(self, tornado_app, *args, **kw):
        self.application_context = kw['application_context']
        self.bokeh_websocket_path = kw['bokeh_websocket_path']
        # session is set by self.prepare
        self.stored_session = None
        # Note: tornado_app is stored as self.application
        super(SessionHandler, self).__init__(tornado_app, *args, **kw)

    def initialize(self, *args, **kw):
        pass

    @gen.coroutine
    def get_session(self):
        session_id = self.get_argument("bokeh-session-id", default=None)
        if session_id is None:
            if self.application.generate_session_ids:
                session_id = generate_session_id(secret_key=self.application.secret_key,
                                                 signed=self.application.sign_sessions)
            else:
                log.debug("Server configured not to generate session IDs and none was provided")
                raise HTTPError(status_code=403, reason="No bokeh-session-id provided")
        elif not check_session_id_signature(session_id,
                                            secret_key=self.application.secret_key,
                                            signed=self.application.sign_sessions):
            log.error("Session id had invalid signature: %r", session_id)
            raise HTTPError(status_code=403, reason="Invalid session ID")

        session = yield self.application_context.create_session_if_needed(session_id, self.request)

        raise gen.Return(session)

    # this methods are copied from example TornadeSessionHandler. They store sessions provided by Tornado and Requests
    def prepare(self):
        super(SessionHandler, self).prepare()
        self.stored_session = setup_session(self)

    def on_finish(self, *args, **kwargs):
        super(SessionHandler, self).on_finish()
        save_session(self.stored_session)

    def clear_session(self):
        super(SessionHandler, self).clear_session()
        self.stored_session.clear()
        self.clear_cookie('session')


