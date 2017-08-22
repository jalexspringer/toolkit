#!/usr/bin/env python

"""
Clone the master onboarding JIRA ticket with subtasks and rename to the new advertiser
"""

import re
import os
import yaml
import db_manage

from subprocess import call

from resources import login, sfdc_details


def generate_parent_issue(j, template, req, opp, account, rep, se):
    name, implementation = req["Account_Name__c"], req['Implementation_Type__c']
    event_type = req["Traffic_Type__c"]
    technology = req["Detection_Technology__c"]
    issue_summary = "Forensiq {} Onboarding {} ({} - {})".format(name, implementation, event_type, technology)
    project = template.fields.project.id
    main_issue_dict = {
        'project': {'id': project},
        'summary': issue_summary,
        'description': build_description(req, opp['Id'], account['Id']),
        'issuetype': {'name': template.fields.issuetype.name},
        # 'reporter': {'name': se}, - Testing
        'reporter': {'name': rep},
        'customfield_13844': [{'value': 'US'}]
    }
    try:
        main_issue_dict['assignee'] = {'name': se}
    except:
        main_issue_dict['assignee'] = {'name': "aspringer@impactradius.com"}
    print(main_issue_dict)
    new_issue = j.create_issue(fields = main_issue_dict)
    print("created parent: {}".format(new_issue.key))
    j.create_issue_link(
        type="Cloners",
        inwardIssue = new_issue.key,
        outwardIssue = template.key,
        comment= {
            "body": "Created clone link between {} and {}".format(new_issue.key, template.key)
        }
        )
    return project, new_issue.key


def generate_subtasks(j, project, parent_issue, subs, req, rep, se):
    name = req["Account_Name__c"]
    subtasks = {}
    for ix, s in enumerate(subs):
        listing = j.issue(s)
        task = {
            'project' : { 'id' : project},
            'summary' : listing.fields.summary + ' - ' + name,
            'issuetype': {'name': listing.fields.issuetype.name},
            'parent' : { 'id' : parent_issue},
            'assignee': {'name': se},
            # 'reporter': {'name': se}
            'reporter': {'name': rep}
        }
        subtasks[ix] = task
    task_ids=[]
    for key,task in subtasks.items():
        child = j.create_issue(fields=task)
        print(task)
        print("created child: " + child.fields.summary + child.key)
        task_ids.append((child.key, child.fields.summary))
    return task_ids


def build_description(req, accountID, oppID):
    sfdc_url = "https://impactradius.my.salesforce.com/{}"
    notes_list = ['Brief_Notes__c', 'Trial_Request_Notes__c']
    notes = ""
    for n in notes_list:
        try:
            notes += req[n]
            notes += "\n"
        except:
            notes += ""
    description = (
        "AE Notes: {} \n\n"
        "Account: {} \n"
        "Opportunity: {} \n"
        "Trial Request: {} \n\n"
        )
    return description.format(notes, sfdc_url.format(accountID), sfdc_url.format(oppID), sfdc_url.format(req['Id']))


def clone_template_ticket(account, opp, req, rep, se):
    j = login()
    if j == "Authentication failed.":
        return j
    template = j.issue(TEMPLATE_ISSUE)
    subs = template.fields.subtasks
    project, parent_issue = generate_parent_issue(j, template, req, opp, account, rep, se)
    subtask_list = generate_subtasks(j, project, parent_issue, subs, req, rep, se)
    issue_list = "Parent Issue: {}\n*** Subtasks:\n".format(parent_issue)
    for i in subtask_list:
        issue_list += "**** {}: {}\n".format(i[0], i[1])
    return issue_list, parent_issue


def createJIRA(oppID):
    account, opp, req, rep, se = sfdc_details(oppID, status='In Progress')
    task_list, parent_issue = clone_template_ticket(account, opp, req, rep, se)
    # org_list = new_task(e, task_list, parent_issue)
    # parent_issues.append(parent_issue)
    sfdc_details(oppID, jira='https://estalea.atlassian.net/browse/{}'.format(parent_issue))
    return parent_issue, rep, se, req['Account_Name__c']


def updateJIRA(oppID, jira, param_dict, traffic_dict, s, orgID):
    account, opp, req, rep, se = sfdc_details(oppID, orgID=orgID)
    server = req['Implementation_Platform__c']
    tech = req['Detection_Technology__c']
    param_string = ''
    traffic_string = ''
    for p, v in param_dict.items():
        param_string += '{}: {}\n'.format(p,v)
    for t, v in traffic_dict.items():
        traffic_string += '{}: {}\n'.format(t,v)
    with open('snippets/display_survey.txt', 'r') as f:
        update = f.read().format(server, tech, param_string, s, traffic_string)
    j = login()
    issue = j.issue(jira)
    description = issue.fields.description
    update = description + '\n\n' + update
    issue.update(fields={'description': update, 'labels': [orgID, 'freetrial']})

    return update, server, tech


def post_comment(jira, comment):
    j = login()
    j.add_comment(jira, comment)
    return 'Commented on issue: {}'.format(jira)


def reassign_task(jira, task, comment, assignee=None):
    j = login()
    if task == 'analysis':
        with open('config.yml', 'r') as config_file:
            cfg = yaml.load(config_file)
            assignee = cfg['analysis_contact']
        analysis_issue = jira[:4] + str((int(jira[4:]) + 5))
        j.assign_issue(analysis_issue, assignee)
        done = post_comment(jira, comment)
        return 'Analysis on issue {} reassigned to {}'.format(jira, assignee)
    elif task == 'tutorial':
        if assignee is not None:
            tutorial_issue = jira[4:] + str((int(jira[4:]) + 4))
            j.assign_issue(tutorial_issue, assignee)
            done = post_comment(jira, comment)
            return 'Tutorial on issue {} reassigned to {}'.format(jira, assignee)
        else:
            return 'Error - please include rep for tutorial assignment.'


def read_issue(jira):
    j = login()
    issue = j.issue(jira)
    summary = issue.fields.summary + ' - ' + jira + '\n'
    description = issue.fields.description + '\n'
    comments = ''
    for c in issue.fields.comment.comments:
        body = c.body
        author = c.author
        created = c.created[:10] + ' ' + c.created.split('T')[1][:8]
        comment = "\n{}\n\n  - {}\n  - {}".format(body, author, created)
        comments += comment + '\n'
    results = summary + description + 'Comments:\n' + comments
    return results


def find_subtask(j, parent, task_type):
    issue = j.issue(parent)
    subs = issue.fields.subtasks
    sub_dict = {}
    for ix, s in enumerate(subs):
        listing = j.issue(s)
        sub_dict[listing.key] = listing.fields.summary
    for k,v in sub_dict.items():
        if task_type in v.lower():
            return k
    return 'No dice. Check the task type.'


def resolve_issue(jira, oppID, task_type):
    database = 'data/records.sql'
    j = login()
    if task_type == 'parent':
        conn = db_manage.create_connection(database)
        db_manage.resolve_record(conn, jira)
        account, opp, req, rep, se = sfdc_details(oppID, status='Completed')
    return 'DB updated - status == Completed'
    #     task = j.issue(jira)
    # else:
    #     task = find_subtask(j, jira, task_type)
    # transitions = j.transitions(task)
    # print(task)
    # print(transitions)
    # return task
