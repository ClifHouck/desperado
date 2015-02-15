import re

class InvalidCurrencyFormat(Exception):
    def __init__(self, reason, data):
        self.reason = reason
        self.data   = data

# XXX
# FIXME: We're entering dangerous territory here... test thoroughly before doing anything significant.
# Or maybe replace entirely.
# XXX
class Dollars(object):
    def __init__(self, dollars, cents):
        self.dollars    = dollars 
        self.cents      = cents
        self.only_cents = dollars * 100 + cents

    def to_cents(self):
        return self.only_cents

    @staticmethod
    def from_cents(cents):
        dollars = cents // 100
        cents   = cents % 100
        return Dollars(dollars, cents)

    @staticmethod
    def from_string(text):
        dollars, cents = Dollars.__parse_string(text)
        return Dollars(dollars, cents)

    @staticmethod
    def __parse_string(text):
        match = re.search("(\d+)\.(\d+)", text)
        if match:
            return (int(match.group(1)), int(match.group(2)))

        raise InvalidCurrencyFormat("Could not convert string into a dollar amount.", text)

    def __add__(self, other):
        total_cents = self.only_cents + other.only_cents
        return Dollars.from_cents(total_cents)

    def __str__(self):
        return "$%d.%02d" % (self.dollars, self.cents)

    
