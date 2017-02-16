from osbrain import run_agent


if __name__ == '__main__':
    a1 = run_agent('a1')
    addr1 = a1.bind('PUB', 'alias1', serializer='raw')

    _address = a1.get_attr('address')
    assert _address[addr1].serializer == 'raw'
