''' Transaction rollbacks'''

import logging
from asyncio import coroutine

logger = logging.getLogger(__name__)

class Rollback(object):
    '''A rollback manager that triggers reads until the txs are rolled back.

    A queue of transactions to rollback with associated bucket + key is kept.
When processing the queue is incrementally walked and for each item a read is issued to trigger a read repair with set of txs in mind.
    '''

    def __init__(self, models):
        self.models = {m.bucket: m for m in models}
        self.txs = ()
        self._queue = []
        self._processing = False

    def queue(self, bucket, key, txid):
        '''Queue a transaction to be rolled back'''

        self._queue.append((bucket, key, txid))

    @coroutine
    def process(self, db):
        '''Trigger read repairs until the queue is empty'''

        # Make sure only one process coroutine is running
        if self._processing:
            logger.info('already processing rollback queue')
            return

        self._processing = True
        logger.info('processing rollback queue')

        try:
            while len(self._queue) > 0:
                self.txs = [q[-1] for q in self._queue]

                (bucket, key, txid) = self._queue.pop()
                logger.info('should rollback %r in %s/%s', txid, bucket, key)

                # This may trigger more transactions to be added to the queue
                model = yield from self.models[bucket].read(db, self, key)

            self.txs = []
        finally:
            self._processing = False
