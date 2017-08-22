import re
import resources
import requests

def format_tag(tag, highlighters=['p','a','cmp','dmn', 'rd']):
    if '[CDATA[' in tag:
        tag = tag.replace('<', '&lt;')
        print(tag, '\n')
    splitted = re.sub('^.*?\?', '', tag).split('&')
    index_counter = 0
    for s in splitted:
        sp = s.split('=')
        if sp[0] in highlighters:
            splitted[index_counter] = '{}=<span style="background:yellow;">{}</span>'.format(sp[0], sp[1])
        index_counter += 1
    formatted = '<code>' + tag.split('?')[0] + '?' + '&'.join(splitted) + '</code>'
    return formatted


def compile_opener(opp, orgID, custom_params, tech, req):
    imp_emails = {
        'Performance Tag/RT API': 'stock_rtapi_params.txt',
        'Display Tag': 'stock_display_params.txt',
        'Pre-bid API': 'prebid.txt',
        'Pre-bid API and Firewall tag': 'prebid_firewall.txt',
        'CAKE Integration': 'cake.txt',
        'HasOffers Integration': 'hasoffers.txt'
    }
    sf = resources.sfdc_login()
    if req['Business_Contact__c']:
        contact = sf.Contact.get(req['Business_Contact__c'])
    else:
        contact = sf.Contact.get(req['Tech_Contact__c'])
    contact = contact['FirstName']

    # TODO Add client key somehow (add to db?)
    # if "API" in tech:
    #     main_intro += "\n<p>Client Key: {}</p>".format('CLIENTKEY')

    main_intro, params, tag_intro = '', '', ''
    need_tag = False
    with open('snippets/main_intro.txt', 'r') as f:
        main_intro = f.read().format(contact, tech, orgID)
    if tech == imp_emails['Performance Tag/RT API']:
        need_tag = 'perf'
    elif tech == imp_emails['Display Tag']:
        need_tag = 'display'

    with open('snippets/{}'.format(imp_emails[tech]), 'r') as f:
        params = f.read()

    opener = '{}\n{}\n{}'.format(main_intro, params, tag_intro)
    return opener, need_tag


def open_stock_tags(orgID, tech, ck):
    print('Stock tags: {}'.format(tech))
    if tech == 'display':
        with open('snippets/gen_display_tag.txt', 'r') as f:
            tags = f.read().format(orgID, orgID, orgID)
    elif tech == 'perf':
        with open('snippets/gen_perf_api.txt', 'r') as f:
            tags = f.read().format(orgID, orgID, ck)
    return tags


def compile_email(oppID, orgID, tags, custom_params={}, tech=None, ck='CLIENTKEY'):
    account, opp, req, rep, se = resources.sfdc_details(oppID)
    print(tech)
    opener, need_tag = compile_opener(opp, orgID, custom_params, tech, req)
    if need_tag:
        tags = open_stock_tags(orgID, need_tag, ck)
    sig = ''
    with open('snippets/sig.txt', 'r') as f:
        sig = f.read()
    email = '{}\n{}\n{}\n'.format(opener, tags, sig)
    return email
