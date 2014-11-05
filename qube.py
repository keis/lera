def add_apply(o, k, p):
    s = o[k]
    if p in s:
        raise KeyError('%s already in set', p)
    s.add(p)


def add_reverse(o, k, p):
    o[k].discard(p)


def rem_apply(o, k, p):
    o[k].remove(p)


def rem_reverse(o, k, p):
    o[k].add(p)


def change_apply(o, k, p):
    frm, to = p

    if o[k] != frm:
        raise ValueError('expected %s to be %s, was %s' % (k, frm, o[k]))

    o[k] = to


def change_reverse(o, k, p):
    frm, to = p
    change_apply(o, k, (to, frm))


APPLY, REVERSE = range(2)

operations = {
    'add': (add_apply, add_reverse),
    'rem': (rem_apply, rem_reverse),
    'change': (change_apply, change_reverse)
}

def rzip(*seqs):
    l = min([len(s) for s in seqs]) - 1
    return zip(*[s[l::-1] for s in seqs])


def apply_op(qube, op):
    name, key, arg, tx = op

    qube['sequence'] += 1
    operations[name][APPLY](qube['data'], key, arg)
    qube['journal'].append((qube['sequence'], name, key, arg, tx))


def init(data=None):
    return {
        'sequence': 0,
        'journal': [],
        'data': data or {},
        'rollback': set()
    }


def from_json(raw):
    qube = {}
    qube.update(raw)

    data = qube['data']
    journal = qube['journal']
    seq = qube['sequence']

    # Convert parts of data to their proper data types
    for k, v in data.items():
        if isinstance(v, list):
            data[k] = set(v)

    # Convert journal entries to tuples
    qube['journal'] = [tuple(j) for j in journal]

    # Convert rollback list to set
    qube['rollback'] = set(qube.get('rollback', ()))

    return qube


def to_json(qube):
    data = qube['data']
    journal = qube['journal']
    seq = qube['sequence']
    rollback = qube['rollback']

    return {
        'data': {k: (list(v) if isinstance(v, set) else v) for k, v in data.items()},
        'journal': [list(j) for j in journal],
        'sequence': seq,
        'rollback': list(rollback)
    }


# TODO allow seq to be given and rollback could be written in terms of merge
#      or create a new function with that functionality
def merge(*qubes, error=None):
    # Find the last common journal entry
    for js in rzip(*[q['journal'] for q in qubes]):
        if js[:-1] == js[1:]:
            break
    else:
        raise Exception('no common journal entry')

    seq = js[0][0]

    # Let base be the qube with the lowest sequence number
    base, *other = sorted(qubes, key=lambda q: q['sequence'])
    data = base['data']

    # Update list of rolled back txs
    base['rollback'].update(*[o['rollback'] for o in other])

    # Assemble a queue of operations to replay. Duplicates operations where the
    # transaction id matches is silently ignored.
    # TODO: Consider a more opportunistic approach of ignoring errors from duplicates
    queue = []
    for q in qubes:
        for o in q['journal'][seq:]:
            op = o[1:]
            if op not in queue:
                queue.append(op)
    queue.sort()

    # Reverse the base back to the last common journal entry
    while base['sequence'] > seq:
        _seq, opname, optarget, param = base['journal'].pop()[:4]
        base['sequence'] -= 1
        operations[opname][REVERSE](data, optarget, param)

    # Replay queue of operations
    for op in queue:
        if op[-1] in base['rollback']:
            continue

        with error(op):
            apply_op(base, op)

    return base


def rollback(qube, txid, error=None):
    for j in qube['journal']:
        if j[4] == txid:
            break
    else:
        return qube

    seq = j[0] - 1

    queue = qube['journal'][seq+1:]
    data = qube['data']

    while qube['sequence'] > seq:
        _seq, opname, optarget, param = qube['journal'].pop()[:4]
        qube['sequence'] -= 1
        operations[opname][REVERSE](data, optarget, param)

    # Replay queue of operations
    for op in queue:
        with error(op):
            apply_op(qube, op[1:])

    qube['rollback'].add(txid)

    return qube
