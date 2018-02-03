# -*- coding: utf-8 -*-

from argparse import ArgumentParser
import os
import csv
from datetime import datetime
import time

import pytz

import nemsneak
from nemsneak import util


if __name__ == '__main__':
    parser = ArgumentParser(
        'enumerate all the "infected" accounts.' +
        '"infected" means the accounts which recieved XEM from the root or ' +
        ' an infected account.'
    )
    parser.add_argument('target', help='the root account')
    parser.add_argument(
        '--dt_from',
        help='search after this datetime. specify if of the form ' +
        '%%Y%%m%%d%%H%%M%%S (ex: 20180126000200). (default: 20180126000200)',
        default='20180126000200'
    )
    parser.add_argument(
        '--timezone', help='timezone (default: Asia/Tokyo)',
        default='Asia/Tokyo'
    )
    parser.add_argument(
        '--api_host', help='API Host (default: http://localhost:7890)',
        default='http://localhost:7890'
    )
    args = parser.parse_args()
    tz = pytz.timezone(args.timezone)
    conn = nemsneak.Connection(tz, args.api_host)

    start_time = datetime.now()

    target = args.target
    from_dt = datetime.strptime(args.dt_from, '%Y%m%d%H%M%S').replace(
        tzinfo=tz
    )

    minarin_mosaic = {
        'namespaceId': 'mizunashi.coincheck_stolen_funds_do_not_accept_trades',
        'name': 'owner_of_this_account_is_hacker'
    }

    def is_marked(addr):
        tmp = conn.get('/account/mosaic/owned', {'address': addr})['data']
        time.sleep(0.1)
        for d in tmp:
            if d['mosaicId']['namespaceId'] == minarin_mosaic['namespaceId'] \
                    and d['mosaicId']['name'] == minarin_mosaic['name']:
                return True
        return False

    queue = [(target, from_dt)]
    known = {}

    res = []

    def hook_func(sender, tx):
        print((sender, tx['transaction']['timeStamp']))
        res.append(util.pp_transaction([
            'datetime', 'amount', 'from_address', 'to_address', 'fee'
        ], util.tidy_transaction(
            tx, conn, sender
        )))

    ch = nemsneak.Chaser(
        target, conn,
        hook_func, from_dt, daemon=True
    )

    ch.start()

    ch.join()

    addrs = set(
        [d[2] for d in res if d[2] is not None] +
        [d[3] for d in res if d[3] is not None]
    )

    info = {}

    for addr in addrs:
        whichmin = (None, None, None)
        for d in res:
            if d[3] == addr:
                if whichmin[0] is None or whichmin[0] > d[0]:
                    whichmin = (d[0], d[1], d[2])
        info[addr] = (is_marked(addr), ) + whichmin

    res.sort(key=lambda x: x[0])

    for d in res:
        print(d)

    if not os.path.exists('results'):
        os.makedirs('results')

    with open(os.path.join(
                'results',
                'info_{}.csv'.format(start_time.strftime('%Y%m%d_%H%M%S'))
            ), 'w') as fout:
        wr = csv.writer(fout, lineterminator='\n')
        wr.writerow(['address', 'is_marked', 'first_recieved_at',
                     'first_tx_amount', 'first_tx_sender'])
        for k, v in info.items():
            wr.writerow((k, ) + v)

    with open(os.path.join(
                'results',
                'tx_{}.csv'.format(start_time.strftime('%Y%m%d_%H%M%S'))
            ), 'w') as fout:
        wr = csv.writer(fout, lineterminator='\n')
        wr.writerow(
            ['datetime', 'amount', 'from_address', 'to_address', 'fee']
        )
        wr.writerows(res)
