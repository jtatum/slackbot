import logging
import re
import time
from typing import Any, List, Optional

from slackbot.dispatcher import Message, MessageDispatcher
from slackbot.manager import PluginsManager

logger = logging.getLogger(__name__)


def hide_in_default_reply(func):
    func.slackbot_hide_in_default_reply = True
    return func


class StateMachine:
    class State:
        def __init__(self, state_machine, message, data):
            #  type: (StateMachine, Message, Any) -> None
            self.state_machine = state_machine
            self.message = message
            self.user = message._get_user_id()
            self.channel = message.body['channel']
            self.created = time.time()
            self.data = data
            self.manager = PluginsManager()

        def respond_to(self, func, expression, flags=0):
            #  type: (callable, str, int) -> None
            self.manager.commands['respond_to'][
                re.compile(expression, flags)] = func
            self.state_machine._respond_to(self, func, expression, flags)

    def __init__(self, dispatcher, plugins):
        #  type: (MessageDispatcher, PluginsManager) -> None
        self._dispatcher = dispatcher
        self._plugins = plugins
        self.states = set()
        self.registered_respond_tos = set()
        self.timeout = 300

    def new_state(self, message, data=None):
        #  type: (Message, Optional[Any]) -> self.State
        channel = message.body['channel']
        user = message._get_user_id()
        state = self.state_for(channel, user)
        if state is not None:
            self.states.remove(state)
        state = self.State(self, message, data)
        self.states.add(state)
        return state

    def state_for(self, channel, user):
        #  type: (str, str) -> Optional[self.State]
        self.states = set(
            [s for s in self.states if time.time() - s.created < self.timeout])
        for state in self.states:
            if state.channel == channel and state.user == user:
                return state

    @hide_in_default_reply
    def _respond_to_handler(self, message, *_):
        #  type: (Message, List[Any], Any) -> None
        channel = message.body['channel']
        user = message._get_user_id()

        state = self.state_for(channel, user)
        if state is None:
            return self._dispatcher._default_reply(message.body)
        self.states.remove(state)
        responded = False
        for func, args in state.manager.get_plugins('respond_to',
                                                    message.body.get('text',
                                                                     None)):
            if func:
                responded = True
                func(message, state.data, *args)
        if not responded:
            return self._dispatcher._default_reply(message.body)

    def _respond_to(self, state, func, expression, flags=0):
        #  type: (StateMachine.State, callable, str, int) -> None
        matcher = re.compile(expression, flags)

        # Remove any other states for same channel and user
        existing_state = self.state_for(state.channel, state.user)
        if existing_state is not None and existing_state != state:
            self.states.remove(existing_state)

        if matcher not in self.registered_respond_tos:
            if self._plugins.commands['respond_to'].get(matcher) is not None:
                raise IndexError(
                    'Cannot create state for %s, another respond_to exists: '
                    '%s' % (
                        expression,
                        self._plugins.commands['respond_to'][matcher]))

            self._plugins.add_command('respond_to', matcher,
                                      self._respond_to_handler)
            self.registered_respond_tos.add(matcher)
        logger.info("Registered dynamic respond_to plugin '%s' to '%s'" % (
            func.__name__, expression))
