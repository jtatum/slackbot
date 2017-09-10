# -*- coding: utf-8 -*-

import logging
import os
from glob import glob
from importlib import import_module
from typing import Any

from collections import defaultdict
from six import PY2

from slackbot import settings
from slackbot.utils import to_utf8

logger = logging.getLogger(__name__)


class PluginsManager(object):
    def __init__(self):
        self.new_commands = defaultdict(dict)
        self.commands = {
            'respond_to': {},
            'listen_to': {},
            'default_reply': {}
        }

    def init_plugins(self):
        if hasattr(settings, 'PLUGINS'):
            plugins = settings.PLUGINS
        else:
            plugins = 'slackbot.plugins'

        for plugin in plugins:
            self._load_plugins(plugin)

    def _load_plugins(self, plugin):
        logger.info('loading plugin "%s"', plugin)
        path_name = None

        if PY2:
            import imp

            for mod in plugin.split('.'):
                if path_name is not None:
                    path_name = [path_name]
                _, path_name, _ = imp.find_module(mod, path_name)
        else:
            from importlib.util import find_spec as importlib_find

            path_name = importlib_find(plugin)
            try:
                path_name = path_name.submodule_search_locations[0]
            except TypeError:
                path_name = path_name.origin

        module_list = [plugin]
        if not path_name.endswith('.py'):
            module_list = glob('{}/[!_]*.py'.format(path_name))
            module_list = ['.'.join((plugin, os.path.split(f)[-1][:-3])) for f
                           in module_list]
        for module in module_list:
            try:
                import_module(module)
            except:
                # TODO Better exception handling
                logger.exception('Failed to import %s', module)

    def add_command(self, category, matcher, func):
        """Add a new plugin at runtime

        Using add_command() allows code to add new plugins while the
        PluginManager is iterating through the collection in get_plugins. This
        avoids a "dictionary changed size during iteration" error.
        """
        #  type: (str, Any, callable) -> None
        self.new_commands[category][matcher] = func

    def update_commands(self):
        for new_category in self.new_commands:
            for new_matcher in self.new_commands[new_category]:
                self.commands[new_category][new_matcher] = \
                    self.new_commands[new_category][new_matcher]
        self.new_commands = defaultdict(dict)

    def get_plugins(self, category, text):
        has_matching_plugin = False
        if text is None:
            text = ''
        for matcher in self.commands[category]:
            m = matcher.search(text)
            if m:
                has_matching_plugin = True
                yield self.commands[category][matcher], to_utf8(m.groups())

        if not has_matching_plugin:
            yield None, None

        self.update_commands()
