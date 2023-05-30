from flask import Flask, request
import ldap
import logging
import sys
import os

returnstring="ad_auth_probe{{ldap=\"{valurl}\"}} {val}"

app = Flask(__name__)

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

@app.route('/authenticate', methods=['GET'])
def authenticate():
    username = request.args.get('username')
    logging.info(f'username= {username}|')
    password = request.args.get('password')
    logging.info(f'password= {password}|')
    ldap_conn_string = request.args.get('ldap_conn_string')
    logging.info(f'ldap= {ldap_conn_string}')

    ldap_server = ldap.initialize(ldap_conn_string)
    ldap_server.set_option(ldap.OPT_NETWORK_TIMEOUT, 3.0)
    
    folder_path = '/application/ca_certs/'
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith('.crt'):
                cert_file = os.path.join(folder_path, filename)
                ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, cert_file)
    except FileNotFoundError: pass


    try:
        ldap_server.simple_bind_s(username, password)
        logging.info('success')
        return returnstring.format(val=1, valurl=f'{ldap_conn_string}')
    except ldap.INVALID_CREDENTIALS:
        logging.error('cred invalid')
        logging.exception("message")
        return returnstring.format(val=0, valurl=f'{ldap_conn_string}')
    except ldap.SERVER_DOWN:
        logging.error('server down')
        logging.exception("message")
        return returnstring.format(val=-1, valurl=f'{ldap_conn_string}')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
