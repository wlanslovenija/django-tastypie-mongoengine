import itertools

from django.conf import settings

from tastypie import exceptions, paginator

import bson
from bson import errors

class Paginator(paginator.Paginator):
    """
    Paginator which allows using MongoDB ObjectId as position
    from where to paginate (in positive or negative direction).
    """

    def get_limit(self):
        limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)

        if 'limit' in self.request_data:
            limit = self.request_data['limit']
        elif self.limit is not None:
            limit = self.limit

        try:
            limit = int(limit)
        except ValueError:
            raise exceptions.BadRequest("Invalid limit '%s' provided. Please provide an integer." % limit)

        return limit

    def get_offset(self):
        offset = self.offset

        if 'offset' in self.request_data:
            offset = self.request_data['offset']

        try:
            offset = bson.ObjectId(offset)
        except (TypeError, errors.InvalidId):
            try:
                offset = int(offset)
            except ValueError:
                raise exceptions.BadRequest("Invalid offset '%s' provided. Please provide an ObjectId or an integer." % offset)

        if isinstance(offset, int) and offset < 0:
            raise exceptions.BadRequest("Invalid integer offset '%s' provided. Please provide a non-negative integer." % offset)

        return offset

    def get_slice(self, limit, offset):
        if isinstance(offset, int):
            if limit < 0:
                raise exceptions.BadRequest("Invalid limit '%s' provided. Please provide a non-negative integer." % limit)
            return super(Paginator, self).get_slice(limit, offset)

        # TODO: Very very inefficient, optimize!

        if limit < 0:
            it = reversed(self.objects)
            limit = -limit
        else:
            it = self.objects.__iter__()

        if limit == 0:
            limit = None

        it = itertools.dropwhile(lambda obj: obj.pk != offset, it)
        it = itertools.islice(it, limit)

        return it

    def get_previous(self, limit, offset):
        if isinstance(offset, int):
            return super(Paginator, self).get_previous(limit, offset)

        # We do not support previous URI as the whole idea behind
        # using ObjectId-based offsets is that integer offsets can
        # become obsolete between requests
        return None

    def get_next(self, limit, offset, count):
        if isinstance(offset, int):
            return super(Paginator, self).get_next(limit, offset, count)

        # We do not support next URI as the whole idea behind using
        # ObjectId-based offsets is that integer offsets can become
        # obsolete between requests
        return None
