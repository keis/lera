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

def rzip(seqa, seqb):
    l = min(len(seqa), len(seqb)) - 1
    return zip(seqa[l::-1], seqb[l::-1])


def apply_op(qube, op):
    qube['sequence'] += 1
    operations[op[0]][APPLY](qube['data'], op[1], op[2])
    qube['journal'].append((qube['sequence'],) + op)


def from_json(raw):
    data = raw['data']
    journal = raw['journal']
    seq = raw['sequence']

    # Convert parts of data to their proper data types
    for k, v in data.items():
        if isinstance(v, list):
            data[k] = set(v)


    # Convert journal entries to tuples
    raw['journal'] = [tuple(j) for j in journal]

    return raw


def to_json(qube):
    data = qube['data']
    journal = qube['journal']
    seq = qube['sequence']

    return {
        'data': {k: (list(v) if isinstance(v, set) else v) for k, v in data.items()},
        'journal': [list(j) for j in journal],
        'sequence': seq
    }


def merge(ql, qr, error=None):
    # Find the last common journal entry
    for (jl, jr) in rzip(ql['journal'], qr['journal']):
        if jl == jr:
            break
    else:
        raise Exception('no common journal entry')

    seq = jl[0]

    # Let base be the qube with the lowest sequence number
    base = min(ql, qr, key=lambda q: q['sequence'])
    data = base['data']

    # Assemble a queue of operations to replay
    queue = ql['journal'][seq+1:] + qr['journal'][seq+1:]
    queue.sort()

    # Reverse the base back to the last common journal entry
    while base['sequence'] > seq:
        _seq, opname, optarget, param = base['journal'].pop()[:4]
        base['sequence'] -= 1
        operations[opname][REVERSE](data, optarget, param)

    # Replay queue of operations
    for op in queue:
        with error(op):
            apply_op(base, op[1:])

    return base


def rollback(qube, txid, error=None):
    for j in qube['journal']:
        if j[4] == txid:
            break
    else:
        return qube

    seq = j[0] - 1

    queue = qube['journal'][seq+2:]
    data = qube['data']

    while qube['sequence'] > seq:
        _seq, opname, optarget, param = qube['journal'].pop()[:4]
        qube['sequence'] -= 1
        operations[opname][REVERSE](data, optarget, param)

    # Replay queue of operations
    for op in queue:
        with error(op):
            apply_op(qube, op[1:])

    return qube
