import requests
import argparse
import ast
import time
import jwt
from jwt import PyJWKClient
import json
def check_token(url, token):
    #url = "https://keycloak.some.domain/auth/realms/epf-uat/protocol/openid-connect/certs"

    jwks_client = PyJWKClient(url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    #print("key="+str(signing_key))
    payload = jwt.decode(token, signing_key.key, audience="account",algorithms=["RS256"])
    j=json.loads(str(payload).lower().replace("'","\""))
    if j["typ"]=="bearer" and j["azp"]== "via_ui":
        return True
    else:
        return False

def get_token(url, client_id, username, password):

    # url = 'https://jge-integration-cluster.eng.evs.tv/auth/realms/evs/protocol/openid-connect/token/'

    params = {

        'client_id': client_id,
        'grant_type': 'password',
        'username' : username,
        'password': password
    }
    start = time.time()
    r=requests.post(url, params, verify=False)
    x = r.content.decode('utf-8')
    json_response = json.loads(x)
    r.close()
    return json_response["access_token"]

def create_client(url, token):

    # GET /{realm}/client-session-stats

    # url = url

    headers = {
                'content-type': 'application/json',
                'Authorization' : 'Bearer '+ str(token)
                }

    params = {
                                "clientId" : "testclient",
                                "id":"3",
                                "name": "testclient-3",
                                "description": "TESTCLIENT-3",
                                "enabled": True,
                                "redirectUris":[ "\\" ],
                                "publicClient": True


            }
   #x = requests.post(url, headers=headers, json=params)
    x = requests.get(url,headers=headers)
    print (x)
    return x.content