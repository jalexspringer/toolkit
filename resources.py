import yaml
from jira import JIRA
from simple_salesforce import Salesforce


def login():
    try:
        with open('config.yml', 'r') as config_file:
            cfg = yaml.load(config_file)
            key_cert_data = None
            with open(cfg['jira']['key_cert_location'], 'r') as key_cert_file:
                key_cert_data = key_cert_file.read()

            oauth_dict = {
                'access_token': cfg['jira']['access_token'],
                'access_token_secret': cfg['jira']['access_token'],
                'consumer_key': cfg['jira']['consumer_key'],
                'key_cert': key_cert_data
            }
            j = JIRA('https://estalea.atlassian.net', oauth=oauth_dict)
            return j
    except:
        print("JIRA authentication failed.")


def sfdc_login():
    with open('config.yml', 'r') as config_file:
        cfg = yaml.load(config_file)
        sf = Salesforce(username=cfg['salesforce']['username'], password=cfg['salesforce']['password'], security_token=cfg['salesforce']['token'])
        return sf

def sfdc_details(oppID, status=None, jira=None, orgID=None):
    sf = sfdc_login()
    if jira:
        sf.Opportunity.update(oppID, {'Link_to_JIRA_Ticket__c': jira})
        return
    else:
        if orgID:
            sf.Opportunity.update(oppID, {'FQ_Org_ID__c': orgID})
        query = "SELECT Id FROM Sales_Engineer_Request__c WHERE Opportunity__c = '{}'".format(oppID)
        response = sf.query(query)
        reqID = response['records'][0]['Id']
        req = sf.Sales_Engineer_Request__c.get(reqID)
        opp = sf.Opportunity.get(oppID)
        account = sf.Account.get(opp['AccountId'])
        rep = sf.User.get(opp['OwnerId'])['Email']
        if status:
            sf.Sales_Engineer_Request__c.update(reqID, {'Status__c': status})
        se = sf.User.get(req['Assigned_Sales_Engineer__c'])['Email']
        return account, opp, req, rep, se

def get_jira_ticket(oppID):
    with open('config.yml', 'r') as config_file:
        cfg = yaml.load(config_file)
        sf = Salesforce(username=cfg['salesforce']['username'], password=cfg['salesforce']['password'], security_token=cfg['salesforce']['token'])
        return sf.Opportunity.get(oppID)['Link_to_JIRA_Ticket__c'][-9:]


def get_orgID(oppID):
    with open('config.yml', 'r') as config_file:
        cfg = yaml.load(config_file)
        sf = Salesforce(username=cfg['salesforce']['username'], password=cfg['salesforce']['password'], security_token=cfg['salesforce']['token'])
        return sf.Opportunity.get(oppID)['FQ_Org_ID__c']
