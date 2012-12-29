# Author: Zhang Huangbin <zhb _at_ iredmail.org>

# Purpose: Apply access policy on sender while recipient is an mail alias.

# Available access policies:
#   - public:   Unrestricted
#   - domain:   Only users under same domain are allowed.
#   - subdomain:    Only users under same domain and sub domains are allowed.
#   - membersOnly:  Only members are allowed.
#   - moderatorsOnly:   Only moderators are allowed.
#   - membersAndModeratorsOnly: Only members and moderators are allowed.

import logging
from web import sqlquote
from libs import SMTP_ACTIONS

REQUIRE_LOCAL_SENDER_= False
REQUIRE_LOCAL_RECIPIENT = True

# Policies. MUST be defined in lower case.
POLICY_PUBLIC = 'public'
POLICY_DOMAIN = 'domain'
POLICY_SUBDOMAIN = 'subdomain'
POLICY_MEMBERSONLY = 'membersonly'
POLICY_MODERATORSONLY = 'moderatorsonly'
POLICY_ALLOWEDONLY = 'allowedonly'      # Same as @POLICY_MODERATORSONLY
POLICY_MEMBERSANDMODERATORSONLY = 'membersandmoderatorsonly'

def restriction(dbConn, senderReceiver, smtpSessionData, **kargs):

    sql = '''SELECT accesspolicy, goto, moderators
            FROM alias
            WHERE
                address=%s
                AND address <> goto
                AND domain=%s
                AND active=1
            LIMIT 1
    ''' % (sqlquote(senderReceiver.get('recipient')),
           sqlquote(senderReceiver.get('recipient_domain')),
          )
    logging.debug('SQL: %s' % sql)

    dbConn.execute(sql)
    sqlRecord = dbConn.fetchone()
    logging.debug('SQL Record: %s' % str(sqlRecord))

    # Recipient account doesn't exist.
    if sqlRecord is None:
        return 'DUNNO (Not mail alias)'

    policy = str(sqlRecord[0]).lower()

    members = [str(v.lower()) for v in str(sqlRecord[1]).split(',')]
    moderators = [str(v.lower()) for v in str(sqlRecord[2]).split(',')]

    logging.debug('policy: %s' % policy)
    logging.debug('members: %s' % ', '.join(members))
    logging.debug('moderators: %s' % ', '.join(moderators))

    if not len(policy) > 0:
        return 'DUNNO (No access policy)'

    if policy == POLICY_PUBLIC:
        # Return if no access policy available or policy is @POLICY_PUBLIC.
        return 'DUNNO'
    elif policy == POLICY_DOMAIN:
        # Bypass all users under the same domain.
        if senderReceiver['sender_domain'] == senderReceiver['recipient_domain']:
            return 'DUNNO'
        else:
            return SMTP_ACTIONS['reject']
    elif policy == POLICY_SUBDOMAIN:
        # Bypass all users under the same domain or sub domains.
        if senderReceiver['sender'].endswith(senderReceiver['recipient_domain']) or \
           senderReceiver['sender'].endswith('.' + senderReceiver['recipient_domain']):
            return 'DUNNO'
        else:
            return SMTP_ACTIONS['reject']
    elif policy == POLICY_MEMBERSONLY:
        # Bypass all members.
        if senderReceiver['sender'] in members:
            return 'DUNNO'
        else:
            return SMTP_ACTIONS['reject']
    elif policy == POLICY_MODERATORSONLY or policy == POLICY_ALLOWEDONLY:
        # Bypass all moderators.
        if senderReceiver['sender'] in moderators:
            return 'DUNNO'
        else:
            return SMTP_ACTIONS['reject']
    elif policy == POLICY_MEMBERSANDMODERATORSONLY:
        # Bypass both members and moderators.
        if senderReceiver['sender'] in members or senderReceiver['sender'] in moderators:
            return 'DUNNO'
        else:
            return SMTP_ACTIONS['reject']
    else:
        # Bypass all if policy is not defined in this plugin.
        return 'DUNNO (Policy is not defined: %s)' % policy