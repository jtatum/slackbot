import re

from slackbot.bot import respond_to, state_machine
from slackbot.dispatcher import Message


@respond_to(r'^create (\w+)')
def create(message, thing):
    """Create a given thing"""
    #  type: (Message, str) -> None
    message.reply('How many {}(s) would you like?'.format(thing))
    # new_state replaces any existing state machine for this user in this
    # channel. It takes the message and an optional data parameter.
    state = state_machine.new_state(message, {'thing': thing})
    state.respond_to(quantity, '(\d+)')


def quantity(message, data, qty):
    """Specify the quantity of thing"""
    #  type: (Message, dict, int) -> None
    data['qty'] = qty
    message.reply(
        'Making {} {}(s), are you sure? (yes/no)'.format(qty, data['thing']))
    state = state_machine.new_state(message, data)
    state.respond_to(yes, 'yes', re.IGNORECASE)
    state.respond_to(no, 'no', re.IGNORECASE)


def yes(message, data):
    """Confirm the creation"""
    #  type: (Message, dict) -> None
    message.reply('Creating {} {}(s)!'.format(data['qty'], data['thing']))


# In general, respond_tos created via the state machine shouldn't appear in
# help. This is an exception, since it has an ordinary @respond_to defined.
@respond_to('(nope)')
def no(message, _):
    """Cancel the creation"""
    #  type: (Message, Any) -> None
    message.reply('Cancelling operation')
