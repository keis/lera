room = bucket 'rooms'
user = bucket 'users'
occupants = bucket 'occupants', {allow_mult: true}

room 'start', ->
    this.description = "A small glade with a air of tranquillity. To the north of here is a opening to a cave. A small trail leads into the forest to the west"
    link ['rooms', 'cave'], 'north'
    link ['rooms', 'forest'], 'west'

occupants 'start', ->
    this.sequence = 2
    this.data = {occupants: ['foo', 'bar']}
    this.journal = [
        [1, 'add', 'occupants', 'foo', 'test-123'],
        [2, 'add', 'occupants', 'bar', 'test-124']
    ]

    sibling ->
        this.sequence = 3
        this.data = {occupants: ['bar']}
        this.journal = [
            [1, 'add', 'occupants', 'foo', 'test-123'],
            [2, 'add', 'occupants', 'bar', 'test-124']
            [3, 'rem', 'occupants', 'foo', 'test-125']
        ]

    sibling ->
        this.sequence = 3
        this.data = {occupants: ['bar']}
        this.journal = [
            [1, 'add', 'occupants', 'foo', 'test-123'],
            [2, 'add', 'occupants', 'bar', 'test-124']
            [3, 'rem', 'occupants', 'foo', 'test-126']
        ]

user 'foo', ->
    this.sequence = 1
    this.data = {
        quest: 'foo',
        room: 'cave'
    }
    this.journal = [
        [1, 'change', 'room', ['start', 'cave'], 'test-125']
    ]

    sibling ->
        this.sequence = 1
        this.data = {
            quest: 'foo',
            room: 'forest'
        }
        this.journal = [
            [1, 'change', 'room', ['start', 'forest'], 'test-126']
        ]

user 'bar', {
    sequence: 0,
    data: {
        quest: 'bar'
    },
    journal: []
}

room 'cave', ->
    this.description = "A cold cave with a altar in the back. On the altar is a collection of cups. Through the entrace of the cave to the south is small glade"
    link ['rooms', 'start'], 'south'

room 'forest', ->
    this.description = "A small trail in the forest. A glade is to the east. To the north is a small brook."
    link ['rooms', 'start'], 'east'
    link ['rooms', 'brook'], 'north'

room 'brook', ->
    this.description = "Blah blah blah. it's a brook."
    link ['rooms', 'forest'], 'south'
    link ['rooms', 'forest'], 'crazy'
