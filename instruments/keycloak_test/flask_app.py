from flask import Flask, Response
from flask import request
from helpers.middleware import setup_metrics
import prometheus_client
import mykeycloak
import urllib.parse
import logging


returnstring="tokenNcheckProbe{{url=\"{valurl}\"}}{val}"
returnstringcheck="tokenNcheckProbe{{url=\"{valurl}\"}}{val}"


CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')


app = Flask(__name__)
#LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(filename='/var/log/record.log', level=logging.DEBUG, format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
app.logger.info('App starting...')
setup_metrics(app)

@app.route('/testkeycloak/')
def testkeycloak():
    #def get_token(url, client_id, username, password):
    myurl = request.args.get('baseurl')
    myurl= urllib.parse.unquote(myurl)
    #print(myurl)
    client_id = request.args.get('client_id')
    username = request.args.get('user')
    password = request.args.get('pass')
    check = request.args.get('check')
    if check == "true":
        try:
            token = mykeycloak.get_token(myurl+"/token",client_id,username,password)
        except BaseException as error:
            app.logger.error('An exception occurred in get_token: {}'.format(error))
            return returnstringcheck.format(val=0, valurl=myurl)
        try:
            if mykeycloak.check_token(myurl+"/certs",token):
                return returnstringcheck.format(val=1, valurl=myurl)
            else:
                return returnstringcheck.format(val=0, valurl=myurl)
        except BaseException as error:
            app.logger.error('An exception occurred in get_token: {}'.format(error))
            return returnstringcheck.format(val=0, valurl=myurl)
        
    else:
        try:
            token = mykeycloak.get_token(myurl,client_id,username,password)
        except BaseException as error:
            app.logger.error('An exception occurred in get_token: {}'.format(error))
            return returnstring.format(val=0, valurl=myurl)
        if token is None:
            return returnstring.format(val=0, valurl=myurl)
        else: 
            return returnstring.format(val=1, valurl=myurl)


@app.route('/testparam')
def testparam():
    myurl = request.args.get('url')
    client_id = request.args.get('client_id')
    username = request.args.get('user')
    password = request.args.get('pass')
    return 'ok {0} {1} {2} {3}'.format(myurl,client_id, username, password)

@app.route('/test/')
def test():
    return 'rest'

@app.route('/test1/')
def test1():
    1/0
    return 'rest'

@app.errorhandler(500)
def handle_500(error):
    return str(error), 500

@app.route('/metrics')
def metrics():
    return Response(prometheus_client.generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run()
