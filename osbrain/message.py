import sys
from enum import Enum


class Types(Enum):
    PING           = 0   # Pin a remote agent
    TEST           = 1   # Test a remote agent
    OK             = 2   # OK response
    ACK            = 3   # Acknowledge response
    ERROR          = 4   # An error ocurred
    DIE            = 5   # Die signal (agent will be terminated)
    UNKNOWN        = 6   # Unrecognized command
    PONG           = 7   # ping default response
    BRAINAWAKE     = 8   # Brain ID: type, [param0, param1, param2...]
    WRONGTYPE      = 9   # Tried to send or received not a Message
    NACK           = 10  # Not ACK
    AGENTSOCK      = 11  # Agent socket
    CONSULT        = 12  # Consult
    NBAR           = 13  # New bar received
    UBAR           = 14  # Notified on bar update
    PYOBJ          = 15  # Any Python object
    AGENTRPP       = 16  # Agent RPP info
    NBRAIN         = 17  # New brain notification
    THINK          = 18  # Brain consult: think
    FLOAT          = 19  # A single float value
    INSUFFDATA     = 20  # Insufficient data
    LISTBARSERIES  = 21  # A list of bar series
    KILLBRAIN      = 22  # Notify component to remove a given brain
    LISTBRAINS     = 23  # Request ist all active brains
    BRAINLIST      = 24  # List of brains
    REMOTEEXEC     = 25  # Remote execution requests
    GETBRAINID     = 26  # Request for the brain id of a brain
    GETBRAINSOCK   = 27  # Request for the agent of a brain
    NHISTBAR       = 28  # New historical bar received
    BRAININFO      = 29  # Request detailed info of a brain
    DBQUERY        = 30  # Request db to the router
    SUBSCRIBE      = 31  # Subscription message
    STATUS         = 32  # Request class variables/status
    DICT           = 33  # Dictionary
    HIST_END       = 34  # End of historical data
    UNSUBSCRIBE    = 35  # Unsubscription message
    LIST           = 36  # List
    DUMP           = 37  # Dump information
    BARSERIES      = 38  # BarSeries object
    DBSUBSCRIBE    = 39  # Subscription to a BarSeries in router
    SYNC           = 40  # Syncronization request
    REQATT         = 41  # Request attention
    REQMEM         = 42  # Request memory
    RELATT         = 43  # Release attention
    SAVESTATE      = 44  # Save state
    GETSTATE       = 45  # Get state
    NBTESTBAR      = 46  # New backtest bar received
    GETORDERS      = 47  # Get orders from strategy brain
    STRCONSULT     = 48  # Consult a brain expecting a string in return
    STR            = 49  # A string (str) type

class Message(object):
    def __init__(self, typ, data = None):

        self.typ = typ
        self.data = data

    def __repr__(self):
        """
        Return the string representation of the Message.

        Returns
        -------
        representation : str
        """
        return '<<%s, %s>>' % (self.typ, self.data)

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        return self.typ == other.typ and \
               self.data == other.data
