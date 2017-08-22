#!/srv/www/engibot/env/bin/python
import ast
import json
import yaml

from tornado import httpserver
from tornado import gen
from tornado.ioloop import IOLoop
import tornado.web
import requests

import resources
import email_format
import db_manage
import send_email

from jira_create import *
from org import get_org_id
from tag_builder import platforms, assemble_tags
from whc import whc


def check_creds(creds):
    return creds == whc

class dbManage(tornado.web.RequestHandler):
    # Initalize database
    def post(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            db_manage.db_init()
            self.write('DB Initialized.')

    # Query database
    def get(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            database = 'data/records.sql'
            try:
                status = tornado.escape.native_str(self.get_argument('status'))
                self.write(db_manage.read_db(db_manage.create_connection(database), locator=loc))
            except:
                status = ''
            try:
                loc = tornado.escape.native_str(self.get_argument('loc'))
                self.write(db_manage.read_db(db_manage.create_connection(database), locator=loc))
            except:
                try:
                    owner = tornado.escape.native_str(self.get_argument('owner'))
                    self.write(db_manage.read_db(db_manage.create_connection(database), owner=owner))
                except:
                    try:
                        rep = tornado.escape.native_str(self.get_argument('rep'))
                        self.write(db_manage.read_db(db_manage.create_connection(database), rep=rep))
                    except:
                        self.write(db_manage.read_db(db_manage.create_connection(database)))


    # Update database records
    def put(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            database = 'data/records.sql'
            if tornado.escape.native_str(self.get_argument('new')) == 'T':
                account = tornado.escape.native_str(self.get_argument('account'))
                oppID = tornado.escape.native_str(self.get_argument('oppID'))
                jira = tornado.escape.native_str(self.get_argument('jira'))
                owner = tornado.escape.native_str(self.get_argument('owner'))
                status = tornado.escape.native_str(self.get_argument('status'))
                rep = tornado.escape.native_str(self.get_argument('rep'))
                try:
                    orgID = tornado.escape.native_str(self.get_argument('orgID'))
                except:
                    orgID = ''
                rowid = db_manage.create_record(db_manage.create_connection(database), (account, oppID, jira, orgID, owner, rep, status))
                self.write('New record created: {}'.format(rowid))
            else:
                oppID = tornado.escape.native_str(self.get_argument('oppID'))
                orgID = tornado.escape.native_str(self.get_argument('orgID'))
                db_manage.update_record(db_manage.create_connection(database), (oppID, orgID))
                self.write('Updated.')


class CreateJIRA(tornado.web.RequestHandler):
    # Generate new JIRA ticket based on salesforce opp and account information.
    def post(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            database = 'data/records.sql'
            try:
                email = tornado.escape.native_str(self.get_argument("email"))
                split = email.split("\n")
                for s in split:
                    if s.startswith("https"):
                        oppID = s.strip()[-15:]
            except:
                oppID = tornado.escape.native_str(self.get_argument("opp"))
                if oppID.startswith("https"):
                    oppID = oppID[-15:].strip()
            if oppID:
                # Status change of se request
                jira, rep, se, account = createJIRA(oppID)
                resources.sfdc_details(oppID, status="In Progress")
                response = {
                    'jira': jira,
                    'oppID': oppID,
                    'rep': rep,
                    'owner': se,
                    'account': account
                }
                self.write(response)
                rowid = db_manage.create_record(db_manage.create_connection(database), (account, oppID, jira, '', se, rep, 'Open'))
            else:
                self.write("Error")
        else:
            self.write('Invalid Credentials.')


class UpdateJIRA(tornado.web.RequestHandler):
    # Client implementation details updated in JIRA ticket
    def post(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            default_params = """{
            }"""
            default_traffic = """{
            }"""

            param_dict = ast.literal_eval(self.get_argument('custom', default_params))
            traffic_dict = ast.literal_eval(self.get_argument('traffic', default_traffic))
            oppID = tornado.escape.native_str(self.get_argument('oppID'))
            orgID = tornado.escape.native_str(self.get_argument('orgID'))
            s = tornado.escape.native_str(self.get_argument('s', 'No'))
            jira = tornado.escape.native_str(self.get_argument('jira'))
            update, server, tech = updateJIRA(oppID, jira, param_dict, traffic_dict, s, orgID)
            response = {
                'params': param_dict,
                'traffic': traffic_dict,
                'server': server,
                'tech': tech
            }
            self.write(json.dumps(response))
        else:
            self.write('Invalid Credentials.')


class Instructions(tornado.web.RequestHandler):
    # Generate implementation instruction email based on client use case
    def get(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            database = 'data/records.sql'
            loc = tornado.escape.native_str(self.get_argument('oppID'))
            tags = tornado.escape.native_str(self.get_argument('tags', ''))
            tech = tornado.escape.native_str(self.get_argument('tech'))
            print(tech)
            record = db_manage.read_db(db_manage.create_connection(database), locator=loc)[0]
            account, oppID, jira, orgID, owner, rep = record[0], record[1], record[2], record[3], record[4], record[5]
            email = email_format.compile_email(oppID, orgID, tags, tech=tech)
            self.write(email)
        else:
            self.write('Invalid Credentials.')

class SendEmail(tornado.web.RequestHandler):
    # Sends email...
    def post(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            body = tornado.escape.native_str(self.get_argument('body'))
            user = tornado.escape.native_str(self.get_argument('user'))
            orgID = tornado.escape.native_str(self.get_argument('orgID'))
            to = tornado.escape.native_str(self.get_argument('to'))
            cc = tornado.escape.native_str(self.get_argument('cc'))
            subject = tornado.escape.native_str(self.get_argument('sub'))
            attachments = tornado.escape.native_str(self.get_argument('attachments'))
            cfg = ''
            with open('/home/{}/config.yml'.format(user), 'r') as config_file:
                cfg = yaml.load(config_file)
            owner = cfg['gmail']['email']
            pw = cfg['gmail']['password']
            send_email.py_mail(subject, body, to, owner, attachments, pw, cc)
            self.write("Email sent to {}!".format(to))
        else:
            self.write('Invalid Credentials.')

    # Grab details from salesforce for email header info.
    def get(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            oppID = tornado.escape.native_str(self.get_argument('oppID'))
            account, opp, req, rep, se = resources.sfdc_details(oppID)
            sf = resources.sfdc_login()
            res_dictionary = {'contacts': {}, 'type': req['Implementation_Type__c']}
            print(req['Tech_Contact__c'])
            try:
                contact = sf.Contact.get(req['Tech_Contact__c'])
                res_dictionary['contacts']['tech'] = [contact['Name'], contact['Email']]
            except:
                print('No tech contact')
            if req['Business_Contact__c'] != req['Tech_Contact__c']:
                try:
                    contact = sf.Contact.get(req['Business_Contact__c'])
                    res_dictionary['contacts']['business'] = [contact['Name'], contact['Email']]
                except:
                    print('No business contact')
            self.write(res_dictionary)
        else:
            self.write('Invalid Credentials.')

class Platforms(tornado.web.RequestHandler):
    # List known platform macros
    def get(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            self.write(platforms())
        else:
            self.write('Invalid Credentials.')


class modJIRA(tornado.web.RequestHandler):
    # Comment or reassign JIRA tasks and subtasks
    def post(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            response = ''
            jira = tornado.escape.native_str(self.get_argument('jira'))
            comment = tornado.escape.native_str(self.get_argument('comment'))
            reassign = tornado.escape.native_str(self.get_argument('reassign', ''))
            response += post_comment(jira, comment) + '\n'
            if reassign != '':
                response = reassign_task(jira, reassign, comment)
            self.write(response)
        else:
            self.write('Invalid Credentials.')

    # Read JIRA ticket comments and summary
    def get(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            jira = tornado.escape.native_str(self.get_argument('jira'))
            response = read_issue(jira)
            self.write(response)
        else:
            self.write('Invalid Credentials.')

    # Resolve JIRA tasks
    def put(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            jira = tornado.escape.native_str(self.get_argument('jira'))
            oppID = tornado.escape.native_str(self.get_argument('oppID'))
            task_type = tornado.escape.native_str(self.get_argument('task'))
            response = resolve_issue(jira, oppID, task_type)
            self.write(response)
        else:
            self.write('Invalid Credentials.')

class Tag(tornado.web.RequestHandler):
    # Generate custom client JS tags with keys and macros based on platform. Return in multiple formats (html, plain text, JSON)
    def get(self):
        if check_creds(tornado.escape.native_str(self.get_argument('creds'))):
            try:
                pfms = tornado.escape.native_str(self.get_argument('pfm')).split(',')
                org = tornado.escape.native_str(self.get_argument('org'))
            except:
                self.write('No orgID (org) or platform (pfm) passed in.')
                return

            if len(org) != 20:
                self.write('Invalid orgID - must be 20 characters.')
                return

            oppID = tornado.escape.native_str(self.get_argument('opp', 'False'))
            img = ast.literal_eval(tornado.escape.native_str(self.get_argument('img', 'True')))
            js = ast.literal_eval(tornado.escape.native_str(self.get_argument('js', 'True')))
            devices = tornado.escape.native_str(self.get_argument('devices', 'desktop,mobile_web,in-app')).split(',')
            formats = tornado.escape.native_str(self.get_argument('formats', 'video,banner')).split(',')
            imp_type = tornado.escape.native_str(self.get_argument('imp_type', 'display')).split(',')
            custom_params = tornado.escape.native_str(self.get_argument('custom_params', '')).split(',')
            custom_dictionary = {}
            if custom_params[0] != '':
                for p in custom_params:
                    split = p.split('|')
                    custom_dictionary[split[0]] = split[1]
            try:
                inst = tornado.escape.native_str(self.get_argument('inst'))
                inst = True
            except:
                inst = False
            try:
                comment = tornado.escape.native_str(self.get_argument('comment'))
                comment = True
            except:
                comment = False
            try:
                html = tornado.escape.native_str(self.get_argument('html'))
                html = True
            except:
                html = False
            response = assemble_tags(pfms, org, js, img, devices, formats, custom_params, oppID, inst, html, comment)
            self.write(response)
        else:
            self.write('Invalid Credentials.')


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/CreateJIRA/?", CreateJIRA),
            (r"/UpdateJIRA/?", UpdateJIRA),
            (r"/modJIRA/?", modJIRA),
            (r"/Org/?", Account),
            (r"/Tag/?", Tag),
            (r"/Platforms/?", Platforms),
            (r"/Instructions/?", Instructions),
            (r"/dbManage/?", dbManage),
            (r"/SendEmail/?", SendEmail),
        ]
        tornado.web.Application.__init__(self, handlers)

def main():
    app = Application()
    app.listen()
    IOLoop.instance().start()

if __name__ == '__main__':
    main()
