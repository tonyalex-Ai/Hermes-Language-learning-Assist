"""
Hermes plugins package — project-level plugin extensions.
Re-exports PluginContext from the Hermes framework so that
``from plugins import PluginContext`` works at import time.
"""
from hermes_cli.plugins import PluginContext
